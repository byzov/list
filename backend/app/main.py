import os
from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional, List
from sqlmodel import Field, SQLModel, Session, create_engine, select, Relationship

app = FastAPI()
engine = create_engine(os.getenv("DATABASE_URL"), echo=True)
templates = Jinja2Templates(directory="templates")

# TODO Отправлять с бэка событие обновить список если добавлен item
# TODO Добавить логирование покупок
# TODO Продумать индексы в таблицы
# TODO Сохранять настройки сортировки в куках
# TODO Добавить крестик в текстовое поле для очистки
# TODO 

# FEATURE Отзывы о товарах
# FEATURE Авторизация
# FEATURE Wishlist
# FEATURE Формирование корзины в онлайн-магазине
# FEATURE Привязка товаров из онлайн-магазина
# FEATURE Рекомендации
# FEATURE Выводить на главном экране рекомандации, если список пуст
# FEATURE Темная тема

#
# Models
#

class Category(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str


class Product(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    categoty_id: Optional[int] = Field(default=None, foreign_key="category.id")
    category: Optional[Category] = Relationship()
    items: 'Item' = Relationship()


class Item(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    product_id: int = Field(default=None, foreign_key="product.id")
    product: Product = Relationship()


@app.on_event("startup")
async def startup():
    SQLModel.metadata.create_all(engine)


def get_db():
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()

#
# Страницы
#

# INDEX
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, session: Session = Depends((get_db))):
    query = select(Item)
    items = session.exec(query).all()
    return templates.TemplateResponse('index.html', {"request": request, "items": items})


# PRODUCTS
@app.get("/products/search", response_class=HTMLResponse)
async def product_search(request: Request, session: Session = Depends((get_db))):
    query = select(Product)
    products = session.exec(query).all()
    return templates.TemplateResponse('search.html',
                                      {"request": request, "products": products})

#
# Categories
#
# TODO Ошраничить добавление товаров с одним названием + категорией
# TODO Реализовать добавление категории к продукту
# TODO Реализовать добавление категорий
# TODO Добавить фильтрацию по катеории
# TODO Добавить на главную филтр по категориям
# TODO Сделать сортировку по категории и имени
# TODO Сделать чтобы смайлки выделялись в отдельное поле
# TODO Если выбран фильтр категории, то продукт добавляем в эту категорию

#
# Products
#
# TODO Разобраться с name в /products/ и /products/search, нужно чтобы проставлялся url
# TODO Очищать поле после добавления продукта и скрол до товара
# TODO Добавить подтверждение при удалении товара
# TODO 

# GET products
@app.get("/products/")
async def get_products(request: Request, name: str, session: Session = Depends((get_db))):
    query = select(Product).where(Product.name.like(f'%{name}%'))
    products = session.exec(query).all()
    exists = session.exec(select(Product).where(Product.name == name)).first()
    return templates.TemplateResponse('partials/products.html',
                                      {"request": request, "products": products, "name": name, "exists": exists})

# GET product
@app.get("/products/{product_id}")
async def get_product(product_id: int, request: Request, session: Session = Depends((get_db))):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse('partials/product.html', {"request": request, "product": product})


# GET product form
@app.get("/products/{product_id}/edit")
async def edit_product(product_id: int, request: Request, session: Session = Depends((get_db))):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse('partials/product_form.html', {"request": request, "product": product})


# PUT product
@app.patch("/products/{product_id}", response_class=HTMLResponse)
async def update_product(product_id: int, request: Request, name: str = Form(...), session: Session = Depends((get_db))):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.name = name

    session.add(product)
    session.commit()
    session.refresh(product)
    return templates.TemplateResponse('partials/product.html', {"request": request, "product": product})

# POST product
@app.post("/products/quick_add", response_class=HTMLResponse)
async def quick_add_product(request: Request, name: str = Form(...), session: Session = Depends((get_db))):
    product = Product(name=name)
    session.add(product)
    session.commit()
    session.refresh(product)

    query = select(Product).where(Product.name.like(f'%{name}%'))
    products = session.exec(query).all()
    return templates.TemplateResponse('partials/products.html', {"request": request, "products": products})


# DELETE product
@app.delete("/products/{product_id}")
async def delete_product(product_id: int, request: Request, session: Session = Depends((get_db))):
    query = select(Product).where(Product.id == product_id)
    product = session.exec(query).first()
    session.delete(product)
    session.commit()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# POST products
@app.post("/products/needs", response_class=HTMLResponse)
async def product_needed(request: Request, product_id: int = Form(...), session: Session = Depends((get_db))):
    item = Item(product_id=product_id)
    session.add(item)
    session.commit()
    session.refresh(item)

    product = session.get(Product, product_id)
    return templates.TemplateResponse('partials/product.html', {"request": request, "product": product})


# POST products
@app.post("/products/notneed", response_class=HTMLResponse)
async def product_notneed(request: Request, product_id: int = Form(...), session: Session = Depends((get_db))):
    query = select(Item).where(Item.product_id == product_id)
    item = session.exec(query).first()
    session.delete(item)
    session.commit()
    if not item:
        raise HTTPException(status_code=404, detail="Product not found")

    product = session.get(Product, product_id)
    return templates.TemplateResponse('partials/product.html', {"request": request, "product": product})


#
# Items
#

# POST item
@app.post("/items/", response_class=HTMLResponse)
async def create_item(request: Request, text: str = Form(...), session: Session = Depends((get_db))):
    item = Item(text=text)
    session.add(item)
    session.commit()
    session.refresh(item)
    return templates.TemplateResponse('partials/item.html', {"request": request, "item": item})


# GET items
@app.get("/items/")
async def get_items(request: Request, session: Session = Depends((get_db))):
    query = select(Item)
    items = session.exec(query).all()
    return items


# GET item
@app.get("/items/{item_id}")
async def get_item(item_id: int, request: Request, session: Session = Depends((get_db))):
    query = select(Item).where(Item.id == item_id)
    item = session.exec(query).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse('partials/item.html', {"request": request, "item": item})


# GET item
@app.get("/items/{item_id}/edit", response_class=HTMLResponse)
async def form_item(item_id: int, request: Request, session: Session = Depends((get_db))):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return templates.TemplateResponse('partials/item_form.html', {"request": request, "item": item})


# PUT item
@app.patch("/items/{item_id}", response_class=HTMLResponse)
async def update_item(item_id: int, request: Request, text: str = Form(...), session: Session = Depends((get_db))):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item.text = text

    session.add(item)
    session.commit()
    session.refresh(item)
    return templates.TemplateResponse('partials/item.html', {"request": request, "item": item})


# DELETE item
@app.delete("/items/{item_id}")
async def delete_item(item_id: int, request: Request, session: Session = Depends((get_db))):
    query = select(Item).where(Item.id == item_id)
    item = session.exec(query).first()
    session.delete(item)
    session.commit()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
