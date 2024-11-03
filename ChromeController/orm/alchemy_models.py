from sqlalchemy import Column, Integer, String, Boolean, BigInteger, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Product(Base):
    __tablename__ = 'repricer_product'

    id = Column(String(100), primary_key=True)
    offer_id = Column(String(20), nullable=False)
    name = Column(String(100), nullable=True)
    price = Column(Integer, nullable=False)
    needed_price = Column(Integer, nullable=True)
    to_removal = Column(Boolean, nullable=False)
    is_updating = Column(Boolean, nullable=False)
    last_update = Column(TIMESTAMP(timezone=True), nullable=False)
    shop_id = Column(BigInteger, ForeignKey('repricer_client.id'), nullable=False)
    sku = Column(String(50), nullable=True)

    # Определим связь с моделью Client
    shop = relationship("Client", back_populates="products")


# Пример модели Client для связи
class Client(Base):
    __tablename__ = 'repricer_client'

    id = Column(BigInteger, primary_key=True)
    password = Column(String(128), nullable=False)
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    is_superuser = Column(Boolean, nullable=False)
    username = Column(String(150), nullable=False)
    first_name = Column(String(150), nullable=False)
    last_name = Column(String(150), nullable=False)
    email = Column(String(254), nullable=False)
    is_staff = Column(Boolean, nullable=False)
    is_active = Column(Boolean, nullable=False)
    date_joined = Column(TIMESTAMP(timezone=True), nullable=False)
    api_key = Column(String(50), nullable=False)
    shop_name = Column(String(100), nullable=True)
    shop_avatar = Column(String(100), nullable=True)
    product_blocked = Column(Boolean, nullable=False)
    last_product = Column(String(20), nullable=True)

    # Связь с моделью Product
    products = relationship("Product", back_populates="shop")
