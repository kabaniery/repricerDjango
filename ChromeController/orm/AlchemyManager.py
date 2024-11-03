from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class AlchemyManager:
    DATABASE_URL = "postgresql://repricer_manager:repricerpassword@localhost:5432/repricer"
    engine = None
    maker = None

    @staticmethod
    def initiate():
        AlchemyManager.engine = create_engine(AlchemyManager.DATABASE_URL)
        AlchemyManager.maker = sessionmaker(autocommit=False, autoflush=False, bind=AlchemyManager.engine)

    def __init__(self):
        if AlchemyManager.maker is None:
            AlchemyManager.initiate()

        self.session = AlchemyManager.maker()
        self.it = 0

    def __del__(self):
        self.session.close()

    def add(self, model, push=True):
        self.session.add(model)
        if push:
            self.session.commit()
            self.it = 0
        else:
            self.it += 1
            if self.it == 10:
                self.session.commit()

