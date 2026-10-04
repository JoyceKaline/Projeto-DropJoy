from openai import OpenAI
from ..core.config import get_settings
from ..models import Product

settings = get_settings()

def local_listing(product: Product) -> dict:
    title = product.name.strip()
    description = (
        f"{product.name}\n\n"
        f"Categoria: {product.category}.\n"
        "Anúncio-base gerado pelo DropJoy para revisão antes da publicação. "
        "Confirme especificações, dimensões, garantia e conteúdo da embalagem com o fornecedor."
    )
    keywords = [x.lower() for x in {product.category, *product.name.split()} if len(x) >= 3]
    return {"provider": "local", "model": None, "title": title[:120], "description": description, "keywords": keywords[:12]}

def generate_listing(product: Product, notes: str | None = None) -> dict:
    if not settings.openai_api_key:
        return local_listing(product)

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""Você é o DropJoy AI, especialista em anúncios de marketplace no Brasil.
Crie um anúncio objetivo para o produto abaixo. Não invente especificações técnicas que não foram fornecidas.
Produto: {product.name}
Categoria: {product.category}
Preço sugerido: R$ {product.sale_price:.2f}
Observações adicionais: {notes or 'nenhuma'}

Responda em português com exatamente estas seções:
TÍTULO:
DESCRIÇÃO:
PALAVRAS-CHAVE: (separadas por vírgula)
"""
    response = client.responses.create(model=settings.openai_model, input=prompt)
    return {"provider": "openai", "model": settings.openai_model, "content": response.output_text}
