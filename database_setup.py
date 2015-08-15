import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
Base = declarative_base()

    
class Catalog(Base):
    __tablename__ = 'catalog'
    id = Column(Integer, primary_key = True)
    name = Column(String(80), nullable = False)


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key = True)
    name = Column(String(80), nullable = False)
    image_uri = Column(String(240), nullable = True)


class Catagory(Base):
    __tablename__ = 'catagory'
    id = Column(Integer, primary_key=True)
    description = Column(String(240), nullable=False)
    

class Item(Base):
    __tablename__ = 'item'
    id = Column(Integer, primary_key = True)
    title = Column(String(240), nullable = False)
    content = Column(String(240), nullable = False)
    user_id = Column(Integer, ForeignKey(User.id), nullable = False)
    user = relationship(User)
    catalog_id = Column(Integer, ForeignKey(Catalog.id), nullable = False)
    catalog = relationship(Catalog)
    catagory_id = Column(Integer, ForeignKey(Catagory.id), nullable = True)
    catagory = relationship(Catagory)
    image_uri = Column(String(240), nullable = True)

    @property
    def serialize(self):
        return {
            'id'     :  self.id,
            'user':  self.user_id,
            'catalog'   :  self.catalog_id,
            'content':  self.content
            }
    

### end of file ###
engine = create_engine('sqlite:///catalog.db')
Base.metadata.create_all(engine)
