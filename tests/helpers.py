from sqlalchemy import BigInteger, Engine, MetaData, create_engine
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import (
    FoodOrder,
    FoodOrderItem,
    Guest,
    MenuItem,
    Reservation,
    Room,
    RoomDevice,
    ServiceRequest,
    User,
)


@compiles(BigInteger, "sqlite")
def compile_big_integer_as_integer(_type: BigInteger, _compiler: object, **_: object) -> str:
    """Keep SQLite test primary keys auto-incrementing like PostgreSQL identities."""

    return "INTEGER"


def create_test_database() -> tuple[Engine, sessionmaker[Session]]:
    """Create the subset used by reception tests in an isolated SQLite database."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata = MetaData()
    for table in (
        User.__table__,
        Guest.__table__,
        MenuItem.__table__,
        Room.__table__,
        Reservation.__table__,
        RoomDevice.__table__,
        FoodOrder.__table__,
        ServiceRequest.__table__,
        FoodOrderItem.__table__,
    ):
        table.to_metadata(metadata)

    reservation_table = metadata.tables["reservations"]
    for constraint in list(reservation_table.constraints):
        if isinstance(constraint, ExcludeConstraint):
            reservation_table.constraints.remove(constraint)

    room_device_table = metadata.tables["room_devices"]
    for index in list(room_device_table.indexes):
        if index.name == "uq_room_devices_active_room":
            room_device_table.indexes.remove(index)

    metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, factory
