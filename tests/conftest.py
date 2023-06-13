from queue import Queue
from typing import List, Iterator

from resoto_plugin_example_collector import ExampleAccount, ExampleRegion, ExampleInstance, ExampleVolume
from resotoclient.models import Model, Kind, Property
from pytest import fixture
from resotolib.baseresources import GraphRoot, Cloud
from resotolib.core.actions import CoreFeedback
from resotolib.graph import Graph
from resotolib.types import Json
from sqlalchemy.engine import create_engine, Engine

from resoto_datalink.sql import SqlDefaultUpdater
from resoto_datalink.arrow.model import ArrowModel
from resoto_datalink.arrow.writer import ArrowWriter
from resoto_datalink.arrow.config import ArrowOutputConfig, FileDestination
from pathlib import Path
import shutil
import uuid


@fixture
def model() -> Model:
    kinds: List[Kind] = [
        Kind("string", "str", None, None),
        Kind("int32", "int32", None, None),
        Kind("int64", "int64", None, None),
        Kind("float", "float", None, None),
        Kind("double", "double", None, None),
        Kind("boolean", "boolean", None, None),
        Kind(
            "resource",
            runtime_kind=None,
            properties=[
                Property("id", "string"),
                Property("name", "string"),
            ],
            bases=[],
            aggregate_root=True,
        ),
        Kind(
            "some_instance",
            runtime_kind=None,
            properties=[
                Property("cores", "int32"),
                Property("memory", "int64"),
            ],
            bases=["resource"],
            aggregate_root=True,
            successor_kinds={"default": ["some_volume"]},
        ),
        Kind(
            "some_volume",
            runtime_kind=None,
            properties=[
                Property("capacity", "int32"),
            ],
            bases=["resource"],
            aggregate_root=True,
        ),
    ]
    return Model({k.fqn: k for k in kinds})


@fixture
def example_collector_graph() -> Graph:
    root = GraphRoot(id="root")
    graph = Graph(root=root)
    cloud = Cloud(id="example")
    account = ExampleAccount(id="example-account")
    region = ExampleRegion(id="example-region")
    i1 = ExampleInstance(id="example-instance-1")
    iv1 = ExampleVolume(id="example-volume-1")
    i2 = ExampleInstance(id="example-instance-2")
    iv2 = ExampleVolume(id="example-volume-1")
    graph.add_resource(root, cloud)
    graph.add_resource(cloud, account)
    graph.add_resource(account, region)
    graph.add_resource(region, i1)
    graph.add_resource(i1, iv1)
    graph.add_resource(region, i2)
    graph.add_resource(i2, iv2)
    return graph


@fixture()
def updater(model: Model) -> SqlDefaultUpdater:
    return SqlDefaultUpdater(model)


@fixture()
def parquet_writer(model: Model) -> Iterator[ArrowWriter]:
    parquet_model = ArrowModel(model, "parquet")
    parquet_model.create_schema([])

    p = Path(f"test_parquet_{uuid.uuid4()}")
    p.mkdir(exist_ok=True)
    yield ArrowWriter(parquet_model, ArrowOutputConfig(FileDestination(p), 1, "parquet"))
    shutil.rmtree(p)


@fixture
def engine() -> Engine:
    return create_engine("sqlite:///:memory:")


@fixture
def engine_with_schema(updater: SqlDefaultUpdater) -> Engine:
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        updater.create_schema(connection, [])
    return engine


@fixture
def feedback_queue() -> Queue[Json]:
    return Queue()


@fixture
def core_feedback(feedback_queue: Queue[Json]) -> CoreFeedback:
    return CoreFeedback("datalink", "test", "collect", feedback_queue)