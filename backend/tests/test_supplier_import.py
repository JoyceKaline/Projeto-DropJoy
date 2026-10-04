from app.services.supplier_import import parse_supplier_file

def test_parse_csv_with_brazilian_decimal_and_aliases():
    content = (
        "Código;EAN;Produto;Categoria;Preço Atacado;Estoque;Preço Varejo\n"
        "ABC1;7891234567890;Cafeteira Teste;Eletro;68,90;12;129,90\n"
    ).encode("utf-8")
    rows, errors, meta = parse_supplier_file("catalogo.csv", content)
    assert not errors
    assert len(rows) == 1
    row = rows[0]
    assert row.sku == "ABC1"
    assert row.gtin == "7891234567890"
    assert row.cost == 68.90
    assert row.stock == 12
    assert row.sale_price == 129.90
    assert meta["rows_accepted"] == 1

def test_missing_required_columns_fails():
    content = "sku;produto\n1;Produto\n".encode("utf-8")
    try:
        parse_supplier_file("x.csv", content)
    except ValueError as exc:
        assert "Colunas obrigatórias" in str(exc)
    else:
        raise AssertionError("Era esperado ValueError")
