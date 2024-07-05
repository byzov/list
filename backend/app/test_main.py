import pytest

from bs4 import BeautifulSoup as soup
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from .main import Item, Product, app, get_db, clear

client = TestClient(app)

# TODO: Написать тесты
# - [ ] POST /products/quick_add return many
# - [ ] POST /products/needs повторный вызов
# - [ ] POST /products/quick_add empty
# - [X] PATCH /products/{product_id}
# - [X] GET /items/{item_id}
# - [X] GET /products/{product_id}/edit
# - [X] DELETE /items/{item_id}
# - [X] POST /products/needs
# - [X] POST /products/notneed
# - [X] POST /products/quick_add
# - [X] GET /products/{product_id}
# - [X] DELETE /products/{product_id}


#
# Фикстуры
#

@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):  
    def get_db_override():  
        return session

    app.dependency_overrides[get_db] = get_db_override  

    client = TestClient(app)  
    yield client  
    app.dependency_overrides.clear()


#
# Тесты
#

def test_post_products_needs_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()
    session.refresh(product_1)

    # Запрос
    responce = client.post("/products/needs", data={"product_id": product_1.id})
    parser = soup(responce.text, 'html.parser')

    # Проверка
    assert responce.status_code == 200
    product_el = parser.select(f"#product-{product_1.id}")[0]
    assert product_el
    assert "inlist" in product_el.get("class")
    assert product_el.find("span", attrs={"hx-post": "/products/notneed"})
    assert product_el.find("button", attrs={"hx-get": f"/products/{product_1.id}/edit"})


def test_post_products_notneed_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()
    session.refresh(product_1)

    item_1 = Item(product_id=product_1.id)
    session.add(item_1)
    session.commit()

    # Запрос
    responce = client.post("/products/notneed", data={"product_id": product_1.id})
    parser = soup(responce.text, 'html.parser')

    # Проверка
    assert responce.status_code == 200
    product_el = parser.select(f"#product-{product_1.id}")[0]
    assert product_el
    assert "inlist" not in product_el.get("class")
    assert product_el.find("span", attrs={"hx-post": "/products/needs"})
    assert product_el.find("button", attrs={"hx-get": f"/products/{product_1.id}/edit"})


def test_post_products_quick_add_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "А Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()

    # Запрос
    responce = client.post("/products/quick_add", data={"name": "Тестовый товар"})
    parser = soup(responce.text, 'html.parser')

    # Проверка
    assert responce.status_code == 200
    assert parser.select("#products")
    assert len(parser.select("#products li")) == 2

    product_el = parser.select("#products li")[1]
    id = product_el.get("id").split("-")[1]
    assert product_el.get("id") == f"product-{id}"
    assert product_el.find("span").get("hx-post") == "/products/needs"
    assert product_el.find("span").text == "Тестовый товар"
    assert product_el.find("button").get("hx-get") == f"/products/{id}/edit"


def test_get_product_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()

    # Запрос
    responce = client.get(f"/products/{product_1.id}")
    parser = soup(responce.text, 'html.parser')

    # Проверка
    assert responce.status_code == 200
    product_el = parser.select(f"#product-{product_1.id}")[0]
    assert product_el
    assert product_el.find("span", attrs={"hx-post": "/products/needs"})
    assert product_el.find("span").text == product_1_name
    assert product_el.find("button", attrs={"hx-get": f"/products/{product_1.id}/edit"})


def test_get_product_404(session: Session, client: TestClient):
    responce = client.get("/products/123")
    assert responce.status_code == 404


def test_delete_product_404(session: Session, client: TestClient):
    responce = client.delete("/products/123")
    assert responce.status_code == 404


def test_delete_product_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()

    # Запрос
    responce = client.delete(f"/products/{product_1.id}")

    # Проверка
    assert responce.status_code == 200
    assert session.get(Product, product_1.id) is None


def test_delete_item_404(session: Session, client: TestClient):
    responce = client.delete("/items/123")
    assert responce.status_code == 404


def test_delete_item_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()
    session.refresh(product_1)

    item_1 = Item(product_id=product_1.id)
    session.add(item_1)
    session.commit()

    # Запрос
    responce = client.delete(f"/items/{item_1.id}")

    # Проверка
    assert responce.status_code == 200
    assert session.get(Item, item_1.id) is None


def test_edit_product_404(session: Session, client: TestClient):
    responce = client.get("/products/123")
    assert responce.status_code == 404


def test_edit_product_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()
    session.refresh(product_1)

    # Запрос
    responce = client.get(f"/products/{product_1.id}/edit")
    parser = soup(responce.text, 'html.parser')

    # Проверка
    assert responce.status_code == 200
    product_el = parser.select(f"#product-{product_1.id}")[0]
    assert product_el
    assert "inlist" not in product_el.get("class")
    assert product_el.find(id="productForm", attrs={"hx-patch": f"/products/{product_1.id}"})
    assert product_el.find(id="nameInput", attrs={"value": product_1.name})
    assert product_el.find("button", attrs={"hx-get": f"/products/{product_1.id}"})
    assert product_el.find("button", attrs={"hx-delete": f"/products/{product_1.id}"})


def test_edit_product_in_list_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()
    session.refresh(product_1)

    item_1 = Item(product_id=product_1.id, description="Тестовый комментарий")
    session.add(item_1)
    session.commit()

    # Запрос
    responce = client.get(f"/products/{product_1.id}/edit")
    parser = soup(responce.text, 'html.parser')

    # Проверка
    assert responce.status_code == 200
    product_el = parser.select(f"#product-{product_1.id}")[0]
    assert "inlist" in product_el.get("class")
    assert product_el.find(id="productForm", attrs={"hx-patch": f"/products/{product_1.id}"})
    assert product_el.find(id="nameInput", attrs={"value": product_1.name})
    assert product_el.find(id="descriptionInput", attrs={"value": item_1.description})
    assert product_el.find("button", attrs={"hx-get": f"/products/{product_1.id}"})
    assert product_el.find("button", attrs={"hx-delete": f"/products/{product_1.id}"})


def test_get_item_404(session: Session, client: TestClient):
    responce = client.get("/items/123")
    assert responce.status_code == 404


def test_get_item_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()
    session.refresh(product_1)

    item_1 = Item(product_id=product_1.id, description="Тестовое комментарий")
    session.add(item_1)
    session.commit()

    # Запрос
    responce = client.get(f"/items/{item_1.id}")
    parser = soup(responce.text, 'html.parser')

    # Проверка
    assert responce.status_code == 200
    assert parser.find(id=f"item-{item_1.id}", attrs={"hx-delete": f"/items/{item_1.id}"})
    assert parser.select(f"#item-{item_1.id} .item-name")[0].text == product_1_name
    assert parser.select(f"#item-{item_1.id} .item-description")[0].text == item_1.description


def test_patch_product_404(session: Session, client: TestClient):
    responce = client.patch("/products/123",
                            data={"name": "Тестовый товар", "description": "Тестовый комментарий"})
    assert responce.status_code == 404


def test_patch_product_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()
    session.refresh(product_1)

    # Запрос
    responce = client.patch(f"/products/{product_1.id}", data={"name": "Булочки"})
    parser = soup(responce.text, 'html.parser')

    # Проверка
    assert responce.status_code == 200
    product_el = parser.select(f"#product-{product_1.id}")[0]
    assert product_el
    assert product_el.find("span", attrs={"hx-post": "/products/needs"})
    assert product_el.find("span").text == "Булочки"
    assert product_el.find("button", attrs={"hx-get": f"/products/{product_1.id}/edit"})


def test_patch_product_in_list_200(session: Session, client: TestClient):
    # Добавление тестовых данных
    product_1_name = "Тестовый товар"
    product_1 = Product(name=product_1_name,
                        clear_name=clear(product_1_name))
    session.add(product_1)
    session.commit()
    session.refresh(product_1)

    item_1 = Item(product_id=product_1.id, description="Тестовое комментарий")
    session.add(item_1)
    session.commit()

    # Запрос
    responce = client.patch(f"/products/{product_1.id}",
                            data={"name": "Булочки", "description": "С маком"})
    parser = soup(responce.text, 'html.parser')
    session.refresh(item_1)

    # Проверка
    assert responce.status_code == 200
    product_el = parser.select(f"#product-{product_1.id}")[0]
    assert product_el
    assert product_el.find("span", attrs={"hx-post": "/products/notneed"})
    assert "inlist" in product_el.get("class")
    assert product_el.find("span").text == "Булочки"
    assert product_el.find("button", attrs={"hx-get": f"/products/{product_1.id}/edit"})
    assert item_1.description == "С маком"
