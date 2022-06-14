from base import Session, engine, Base
from schemas import Result as SchemaResult
from schemas import Token as SchemaToken
from models import Result as ModelResult
from models import Token as ModelToken
from pydantic import constr

Base.metadata.create_all(engine)

session = Session()


def create_token(token: SchemaToken):
    db_token = ModelToken(token=token.token)
    session.add(db_token)
    session.commit()
    session.close()
    return db_token


def get_last_token():
    return session.query(ModelToken).order_by(ModelToken.id.desc()).first()


def crete_result(result: SchemaResult):
    db_result = ModelResult(
        iin=result.iin,
        address=result.address,
        numbers=result.numbers,
        status_osms=result.status_osms,
        categories_osms=result.categories_osms,
        relatives=result.relatives,
        death_date=result.death_date
    )
    session.add(db_result)
    session.commit()
    return db_result


def update_result(result: SchemaResult):
    session.query(ModelResult).filter(ModelResult.iin == result.iin).\
        update(result.dict(), synchronize_session="fetch")
    session.commit()
    return result


def get_result_by_iin(iin: constr(min_length=12, max_length=12)):
    db_result = session.query(ModelResult).filter(ModelResult.iin == iin).first()
    return db_result


if __name__ == '__main__':
    print(get_result_by_iin('030228500880'))
