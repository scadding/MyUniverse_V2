
from sqlalchemy import create_engine, text, MetaData, Connection, orm
from sqlalchemy import Table, Column, Integer, String, Text, Uuid
from sqlalchemy import select, column, func, table
from src.Configuration import Configuration
from src.Generators.tablegen.tableNode import tableNode
import uuid

from src.Singleton import Singleton

class databaseManager(metaclass=Singleton):
    config : Configuration
    metadata_obj : MetaData = None
    def __init__(self):
        self.config = Configuration()
        self.loaddb()
    def loaddb(self):
        if not self.config.getValue("Data", "dbconnection"):
            return
        self.engine = create_engine(self.config.getValue("Data", "dbconnection"), echo=False)
        self.metadata_obj = MetaData()
        self.metadata_obj.reflect(self.engine)
        with self.engine.connect() as conn:
            if not self.engine.dialect.has_table(conn, 'universe.Tables'):
                conn.close()
                self.createDatabase()
            else:
                conn.close()
    def loadTree(self, node : tableNode):
        if self.metadata_obj is None:
            return
        table = self.metadata_obj.tables['universe.Nodes']
        statement = select(table.c.Node, table.c.Name).where(table.c.Parent == None)
        with orm.Session(self.engine) as session:
            row = session.execute(statement).first()
            if not row:
                return
            node.uuid = uuid.UUID(row[0])
            self.loadChildren(session, node)
        session.close()
    def loadChildren(self, session : orm.Session, parent : tableNode):
        table = self.metadata_obj.tables['universe.Nodes']
        statement = select(table.c.Node, table.c.Name).where(table.c.Parent == parent.uuid)
        for row in session.execute(statement):
            node = tableNode(row[1], parent=parent, table=None, display=True, uuid=uuid.UUID(row[0]))
            self.loadChildren(session, node)
    def prepareMetaData(self):
        objects = Table(
            "universe.Objects",
            self.metadata_obj,
            Column("Object", Uuid, primary_key=True),
            Column("Node", Uuid, nullable=False),
        )
        Variables = Table(
            "universe.Variables",
            self.metadata_obj,
            Column("Object", Uuid, nullable=False),
            Column("Name", Text, nullable=False),
            Column("Value", Text, nullable=False),
        )
        TableVariables = Table(
            "universe.TableVariables",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("Name", Text, nullable=False),
            Column("Value", Text, nullable=False),
        )
        TableLines = Table(
            "universe.TableLines",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("SubTableName", Text, nullable=False),
            Column("Roll", Integer, nullable=False),
            Column("Line", Text, nullable=False),
        )
        Tables = Table(
            "universe.Tables",
            self.metadata_obj,
            Column("Node", Uuid, nullable=False),
            Column("TableName", Text, nullable=False),
            Column("SubTableName", Text, nullable=False),
            Column("Type", Text, nullable=False),
            Column("Length", Integer, nullable=False),
        )
        Nodes = Table(
            "universe.Nodes",
            self.metadata_obj,
            Column("Node", Uuid, primary_key=True),
            Column("Name", Text, nullable=False),
            Column("Parent", Uuid),
        )
    def createDatabase(self):
        self.prepareMetaData()
        with self.engine.connect() as conn:
            self.metadata_obj.create_all(conn)
            conn.commit()
            conn.close()
