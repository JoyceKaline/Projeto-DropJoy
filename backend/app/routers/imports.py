from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Supplier, Product, Offer, OfferHistory, TenantSupplier, User
from ..core.auth import require_roles
from ..services.audit import audit
from ..services.supplier_import import parse_supplier_file

router = APIRouter(prefix="/api/imports", tags=["imports"])

MAX_FILE_BYTES = 10 * 1024 * 1024

@router.get("/supplier-template.csv")
def supplier_template(admin: User = Depends(require_roles("owner", "admin"))):
    content = (
        "sku;gtin;produto;categoria;custo;estoque;preco_venda;prazo_horas\n"
        "ABC123;7891234567890;Produto exemplo;Casa;39,90;25;69,90;24\n"
    )
    return Response(
        content=content.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="dropjoy-modelo-fornecedor.csv"'},
    )

@router.post("/supplier/{supplier_id}")
async def import_supplier_file(
    supplier_id: int,
    file: UploadFile = File(...),
    admin: User = Depends(require_roles("owner", "admin")),
    session: Session = Depends(get_db),
):
    supplier = session.get(Supplier, supplier_id)
    if not supplier or not supplier.active:
        raise HTTPException(404, "Fornecedor não encontrado")

    filename = file.filename or "arquivo"
    content = await file.read(MAX_FILE_BYTES + 1)
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(413, "Arquivo excede o limite de 10 MB")

    try:
        rows, row_errors, meta = parse_supplier_file(filename, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if not rows:
        raise HTTPException(400, {"message": "Nenhuma linha válida para importar.", "errors": row_errors[:20]})

    link = session.scalar(select(TenantSupplier).where(
        TenantSupplier.tenant_id == admin.tenant_id,
        TenantSupplier.supplier_id == supplier.id,
    ))
    if not link:
        link = TenantSupplier(tenant_id=admin.tenant_id, supplier_id=supplier.id, enabled=True, mode="demo")
        session.add(link)
    else:
        link.enabled = True

    now = datetime.now(timezone.utc)
    created_products = updated_products = created_offers = updated_offers = 0

    for item in rows:
        external_key = f"gtin:{item.gtin}" if item.gtin else f"supplier:{supplier.slug}:{item.sku}"
        product = session.scalar(select(Product).where(Product.external_key == external_key))
        if not product:
            product = Product(
                external_key=external_key,
                name=item.name,
                category=item.category,
                sale_price=item.sale_price,
                competition_score=.75,
            )
            session.add(product)
            session.flush()
            created_products += 1
        else:
            product.name = item.name
            product.category = item.category
            product.sale_price = item.sale_price
            updated_products += 1

        offer = session.scalar(select(Offer).where(
            Offer.product_id == product.id,
            Offer.supplier_id == supplier.id,
        ))
        if not offer:
            offer = Offer(
                product_id=product.id,
                supplier_id=supplier.id,
                supplier_sku=item.sku,
                cost=item.cost,
                stock=item.stock,
                shipping_hours=item.shipping_hours,
                updated_at=now,
            )
            session.add(offer)
            session.flush()
            created_offers += 1
        else:
            offer.supplier_sku = item.sku
            offer.cost = item.cost
            offer.stock = item.stock
            offer.shipping_hours = item.shipping_hours
            offer.updated_at = now
            updated_offers += 1

        session.add(OfferHistory(
            offer_id=offer.id,
            captured_at=now,
            cost=item.cost,
            stock=item.stock,
        ))

    link.last_sync_at = now
    session.commit()

    audit(
        session,
        tenant_id=admin.tenant_id,
        user=admin,
        action="supplier.file_imported",
        entity_type="supplier",
        entity_id=supplier.id,
        details={
            "filename": filename,
            "accepted": len(rows),
            "rejected": len(row_errors),
            "created_products": created_products,
            "updated_products": updated_products,
            "created_offers": created_offers,
            "updated_offers": updated_offers,
        },
    )

    return {
        "status": "ok",
        "supplier": {"id": supplier.id, "name": supplier.name, "slug": supplier.slug},
        "imported_rows": len(rows),
        "rejected_rows": len(row_errors),
        "created_products": created_products,
        "updated_products": updated_products,
        "created_offers": created_offers,
        "updated_offers": updated_offers,
        "errors": row_errors[:20],
        "meta": meta,
    }
