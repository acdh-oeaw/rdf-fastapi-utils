# RDF-FastAPI-Utils
This is a small utils library for providing access to data in a triplestore via a FastAPI Rest endpoint.
Currently it contains only those classes used to convert a Json resulting from a SPARQL query into a given pydantic model.

Currently it contains two classes:
- `models.FieldConfigurationRDF` to add additional information for processing RDF data to the fields in a pydantic model
- and `models.RDFUtilsModelBaseClass` as a pydantic base class to inherit from for adding SPARQL Json to a pydantic model.

## Minimal example
*this is taken from the tests*

models.py:
```python
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

```

test_data.json
```json
{
      "page": 1,
      "count": 1,
      "pages": 1,
      "results": [
            {
                  "count": 1,
                  "person": "http://www.intavia.eu/apis/personproxy/27118",
                  "entityTypeLabel": "person",
                  "entityLabel": "Tesla, Nikola",
                  "linkedIds": "https://apis-edits.acdh-dev.oeaw.ac.at/entity/27118/",
                  "role": "http://www.intavia.eu/apis/deceased_person/27118",
                  "event": "http://www.intavia.eu/apis/deathevent/27118",
                  "evPlace": "http://www.intavia.eu/apis/place/25209",
                  "evPlaceLatLong": "Point ( -74.00597 +40.71427 )",
                  "evPlaceLabel": "New York City",
                  "eventLabel": "Death of Nikola Tesla",
                  "end": "1943-01-07 23:59:59+00:00"
            },
            {
                  "count": 1,
                  "person": "http://www.intavia.eu/apis/personproxy/27118",
                  "entityTypeLabel": "person",
                  "entityLabel": "Tesla, Nikola",
                  "linkedIds": "https://apis.acdh.oeaw.ac.at/entity/27118",
                  "role": "http://www.intavia.eu/apis/deceased_person/27118",
                  "event": "http://www.intavia.eu/apis/deathevent/27118",
                  "evPlace": "http://www.intavia.eu/apis/place/25209",
                  "evPlaceLatLong": "Point ( -74.00597 +40.71427 )",
                  "evPlaceLabel": "New York City",
                  "eventLabel": "Death of Nikola Tesla",
                  "end": "1943-01-07 23:59:59+00:00"
            },
            {
                  "count": 1,
                  "person": "http://www.intavia.eu/apis/personproxy/27118",
                  "entityTypeLabel": "person",
                  "entityLabel": "Tesla, Nikola",
                  "linkedIds": "https://apis-edits.acdh-dev.oeaw.ac.at/entity/27118/",
                  "role": "http://www.intavia.eu/apis/personplace/eventrole/155790",
                  "event": "http://www.intavia.eu/apis/event/personplace/155790",
                  "evPlace": "http://www.intavia.eu/apis/place/129965",
                  "evPlaceLatLong": "Point ( +15.31806 +44.56389 )",
                  "evPlaceLabel": "Smiljan",
                  "roleLabel": "ausgebildet in",
                  "eventLabel": "Tesla, Nikola ausgebildet in Smiljan",
                  "start": "1862-01-01 00:00:00+00:00",
                  "end": "1866-12-31 23:59:59+00:00"
            },
            {
                  "count": 1,
                  "person": "http://www.intavia.eu/apis/personproxy/27118",
                  "entityTypeLabel": "person",
                  "entityLabel": "Tesla, Nikola",
                  "linkedIds": "https://apis.acdh.oeaw.ac.at/entity/27118",
                  "role": "http://www.intavia.eu/apis/personplace/eventrole/155790",
                  "event": "http://www.intavia.eu/apis/event/personplace/155790",
                  "evPlace": "http://www.intavia.eu/apis/place/129965",
                  "evPlaceLatLong": "Point ( +15.31806 +44.56389 )",
                  "evPlaceLabel": "Smiljan",
                  "roleLabel": "ausgebildet in",
                  "eventLabel": "Tesla, Nikola ausgebildet in Smiljan",
                  "start": "1862-01-01 00:00:00+00:00",
                  "end": "1866-12-31 23:59:59+00:00"
            }
      ]
}
```

Running the following with the above files in place will result in a correctly nested python object:

```python
import json
from .models import TCPaginatedResponse

with open("test_data.json") as inp:
    data = json.load(inp)
    res = TCPaginatedResponse(**data)

print(res)
```