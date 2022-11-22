from typing import Union
import unittest
import json
from pydantic import Field
from rdf_fastapi_utils.models import FieldConfigurationRDF, RDFUtilsModelBaseClass


class TCPaginatedResponse(RDFUtilsModelBaseClass):
    count: int = Field(..., rdfconfig=FieldConfigurationRDF(path="count"))
    results: list[Union["TCPersonFull", "TCPlaceFull"]] = Field(
        ...,
        rdfconfig=FieldConfigurationRDF(path="results", serialization_class_callback=lambda field, item: TCPersonFull),
    )


class TCPersonFull(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(anchor=True, path="person"))
    name: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entityLabel"))
    events: list["TCEventFull"] = None


class TCPlaceFull(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(anchor=True, path="person"))
    name: str = Field(..., rdfconfig=FieldConfigurationRDF(path="entityLabel"))
    events: list["TCEventFull"] = None


class TCEventFull(RDFUtilsModelBaseClass):
    id: str = Field(..., rdfconfig=FieldConfigurationRDF(anchor=True, path="event"))
    label: str = Field(..., rdfconfig=FieldConfigurationRDF(path="eventLabel"))


TCPaginatedResponse.update_forward_refs()
TCPersonFull.update_forward_refs()
TCEventFull.update_forward_refs()


class TestInTaViaBaseClass(unittest.TestCase):
    def setUp(self) -> None:
        with open("rdf-fastapi-utils/rdf_fastapi_utils/tests/test_data.json") as f:
            self.test_data = json.load(f)
        with open("rdf-fastapi-utils/rdf_fastapi_utils/tests/test_data_events.json") as f:
            self.test_data_events = json.load(f)
        return super().setUp()

    def test_filter_sparql(self):
        res = InTaViaModelBaseClass().filter_sparql(self.test_data["results"], anchor="person")
        self.assertEqual(len(res), 50)

    def test_filter_sparql_no_values_selected(self):
        res = InTaViaModelBaseClass().filter_sparql(self.test_data["results"], anchor="person", list_of_keys=None)
        for ent in res:
            self.assertFalse("_additional_values" in ent)

    def test_filter_sparql_values_selected(self):
        res = InTaViaModelBaseClass().filter_sparql(
            self.test_data["results"], anchor="person", list_of_keys=["person", "entityLabel"]
        )
        for ent in res:
            self.assertTrue("_additional_values" in ent)

    def test_complex_example(self):
        res = InTaViaModelBaseClass().filter_sparql(
            self.test_data_events["results"], anchor="person", list_of_keys=["person", "entityLabel"]
        )
        res2 = InTaViaModelBaseClass().filter_sparql(
            res[0]["_additional_values"], anchor="event", list_of_keys=["event", "eventLabel", "start"]
        )
        self.assertEqual(len(res2), 14)

    def test_model_field(self):
        res = TCPaginatedResponse(**self.test_data_events)
        self.assertEqual(len(res.results[0].events), 14)
