from copy import deepcopy
import datetime
from typing import Any, Callable, List, Tuple
import typing
from pydantic import BaseModel, Field, constr
from pydantic.fields import ModelField


class FieldConfigurationRDF(BaseModel):
    """Configuration for how to use RDF data in the field"""

    path: constr(regex="^[a-zA-Z0-9\._]+$") | None = Field(
        None, description="RDF variable to use for populating the field"
    )
    anchor: bool = Field(False, description="Whether to use the RDF variable as an anchor")
    default_value: Any = Field(None, description="Default value to use when populating the field")
    callback_function: Callable | None = Field(
        None, description="Callback for posprocessing data from the RDF variable"
    )
    serialization_class_callback: Callable | None = Field(
        None,
        description="Callback function for deciding on the correct class for serialization. Function\
            gets two parameters: field and RDFData and needs to return the class to use.",
    )
    default_dict_key: constr(regex="^[a-zA-Z0-9_]+$") | None = Field(
        None, desctiption="In a related field use this key as default"
    )


class RDFUtilsModelBaseClass(BaseModel):
    @staticmethod
    def harm_filter_sparql(data: list) -> list | None:
        for ent in data:  # FIXME: this is a hack to fix the problem with the filter_sparql function
            if ent:
                return data
        return None

    def filter_sparql(
        self,
        data: list | dict,
        filters: typing.List[typing.Tuple[str, str]] | None = None,
        list_of_keys: typing.List[str] = None,
        anchor: str | None = None,
        additional_values: typing.List[str] | None = None,
    ) -> typing.List[dict] | None:
        """filters sparql result for key value pairs

        Args:
            data (list): array of results from sparql endpoint (python object converted from json return)
            filter (typing.List[tuple]): list of tuples containing key / value pair to filter on
            list_of_keys (typing.List[str], optional): list of keys to return. Defaults to None.
            additional_values (typing.List[str], optional): list of additional values to return. Defaults to None.

        Returns:
            typing.List[dict] | None: list of dictionaries containing keys and values
        """
        if isinstance(data, list):
            if len(data) == 0:
                return []
            if not isinstance(data[0], dict):
                return data
        if isinstance(data, dict):
            data = [data]
        if additional_values is None:
            additional_values = []
            for ent in data:
                for key in ent:
                    if key not in additional_values:
                        additional_values.append(key)
        if filters is not None:
            while len(filters) > 0 and len(data) > 0:
                f1 = filters.pop(0)
                data_res = list(filter(lambda x: (x[f1[0]] == f1[1]), data))
            data = data_res
        if len(data) == 0:
            return None
        # if list_of_keys is not None:
        #     data = [{k: v for k, v in d.items() if k in list_of_keys or k in additional_values} for d in data]
        if list_of_keys is None:
            list_of_keys = []
            for ent in data:
                for key in ent:
                    if key not in list_of_keys:
                        list_of_keys.append(key)
        if anchor is not None:
            lst_unique_vals = set([x[anchor] for x in data])
            res_fin_anchor = []
            for item in lst_unique_vals:
                add_vals = []
                res1 = {}
                for i2 in list(filter(lambda d: d[anchor] == item, data)):
                    add_vals_dict = deepcopy(i2)
                    for k, v in i2.items():
                        if k in list_of_keys or k == anchor:
                            if k not in res1:
                                res1[k] = v
                            else:
                                if (
                                    isinstance(res1[k], str)
                                    or isinstance(res1[k], int)
                                    or isinstance(res1[k], float)
                                    or isinstance(res1[k], datetime.datetime)
                                ):
                                    if v != res1[k]:
                                        res1[k] = [res1[k], v]
                                elif v not in res1[k]:
                                    res1[k].append(v)
                            del add_vals_dict[k]
                    if add_vals_dict:
                        if add_vals_dict not in add_vals:
                            add_vals.append(add_vals_dict)
                if len(add_vals) > 0:
                    if not "_additional_values" in res1:
                        res1["_additional_values"] = add_vals
                    else:
                        res1["_additional_values"].extend(add_vals)
                res_fin_anchor.append(res1)
            return self.harm_filter_sparql(res_fin_anchor)
        else:
            res_fin = []
            for i1 in data:
                for k, v in i1.items():
                    if k in list_of_keys:
                        if isinstance(v, list):
                            for count, it in enumerate(v):
                                if len(res_fin) - 1 < count:
                                    res_fin.append({k: it})
                                else:
                                    res_fin[count][k] = it
                        else:
                            if len(res_fin) > 0:
                                res_fin[0][k] = v
                            else:
                                res_fin.append({k: v})
            return self.harm_filter_sparql(res_fin)
        # return self.harm_filter_sparql(data)

    def get_anchor_element_from_field(self, field: ModelField) -> typing.Tuple[str, ModelField] | None:
        """takes a field class and returns a tuple of the anchor element and the field class

        Args:
            field (ModelField): the field class

        Returns:
            typing.Tuple[str, ModelField] | None: tuple of name and field class of the anchor element, None if no anchor element
        """
        if not getattr(field.type_, "__fields__", False):
            return None
        for f_name, f_class in field.type_.__fields__.items():
            f_conf = f_class.field_info.extra.get("rdfconfig", object())
            if getattr(f_conf, "anchor", False):
                if getattr(f_conf, "path", False):
                    f_name = getattr(f_conf, "path")
                return f_name, f_class
        return None

    def get_anchor_element_from_model(self, model: BaseModel) -> typing.Tuple[str, ModelField] | None:
        """takes a model class and returns a tuple of the anchor element and the field class"""
        for f_name, f_class in model.__fields__.items():
            f_conf = f_class.field_info.extra.get("rdfconfig", object())
            if getattr(f_conf, "anchor", False):
                if getattr(f_conf, "path", False):
                    f_name = getattr(f_conf, "path")
                return f_name, f_class
        return None

    def get_rdf_variables_from_field(self, field: ModelField) -> typing.List[str]:
        res = []
        for f_name, f_class in field.type_.__fields__.items():
            f_conf = f_class.field_info.extra.get("rdfconfig", object())
            if hasattr(f_conf, "path"):
                res.append(f_conf.path)
            else:
                res.append(f_name)
        return res

    def get_rdf_variables_from_model(self, model: BaseModel) -> typing.List[str]:
        res = []
        for f_name, f_class in model.__fields__.items():
            f_conf = f_class.field_info.extra.get("rdfconfig", object())
            if hasattr(f_conf, "path"):
                res.append(f_conf.path)
            else:
                res.append(f_name)
        return res

    def map_fields_data(self, data: dict) -> dict:
        """Unses the field information to map the RDF values to the correct fields

        Args:
            data (dict): input RDF data

        Returns:
            dict: resulting data using the correct maps
        """
        res = {}
        for field in self.__fields__.values():
            path = getattr(field.field_info.extra.get("rdfconfig"), "path", None)
            if path is None:
                path = field.name
            if path not in data:
                continue
            if hasattr(field.type_, "__fields__"):  # FIXME: this test doesnt catch all the options

                scallback_attr = getattr(field.field_info.extra.get("rdfconfig"), "serialization_class_callback", None)
                default_dict_key = getattr(field.field_info.extra.get("rdfconfig"), "default_dict_key", None)
                if scallback_attr is not None:
                    res[field.name] = []
                    if not isinstance(data[path], list):
                        data[path] = [data[path]]
                    # for ent in data[path]:
                    cb = scallback_attr(field, data[path])
                    anchor = self.get_anchor_element_from_model(model=cb)
                    rdf_data = self.filter_sparql(
                        data=data["_additional_values"] if "_additional_values" in data else data[path],
                        anchor=anchor[0],
                        list_of_keys=self.get_rdf_variables_from_model(model=cb),
                    )
                    res[field.name] = [cb(**ent) for ent in rdf_data]
                    if field.outer_type_.__origin__ != list:
                        res[field.name] = res[field.name][0]
                elif (
                    (isinstance(data[path], list) or isinstance(data[path], str))
                    and default_dict_key is not None
                    and isinstance(field.sub_fields, list)
                ):
                    if isinstance(data[path], str):
                        d1 = [data[path]]
                    else:
                        d1 = data[path]
                    res[field.name] = [{default_dict_key: ent} for ent in d1]
                elif (isinstance(data[path], list) or isinstance(data[path], str)) and default_dict_key is not None:
                    if isinstance(data[path], list):
                        d1 = data[path][0]
                    else:
                        d1 = data[path]
                    res[field.name] = {default_dict_key: d1}
                elif isinstance(data[path], list):
                    anchor = self.get_anchor_element_from_model(model=field.type_)
                    res[field.name] = self.filter_sparql(
                        # data=data["_additional_values"] if "_additional_values" in data else data[path],
                        data=data[path],
                        anchor=anchor[0] if anchor is not None else None,
                        list_of_keys=self.get_rdf_variables_from_model(model=field.type_),
                    )
                    print("test")
                else:
                    anchor = self.get_anchor_element_from_model(model=field.type_)
                    res[field.name] = self.filter_sparql(
                        # data=data["_additional_values"] if "_additional_values" in data else data,
                        data=data,
                        anchor=anchor[0] if anchor is not None else None,
                        list_of_keys=self.get_rdf_variables_from_model(model=field.type_),
                    )
            else:
                default_value = getattr(field.field_info.extra.get("rdfconfig"), "default_value", None)
                res[field.name] = data.get(path, default_value)
        return res

    def post_process_data(self, data: dict) -> dict:

        for field in self.__fields__.values():
            cb = getattr(field.field_info.extra.get("rdfconfig"), "callback_function", None)
            if cb is not None and field.name in data:
                data[field.name] = cb(field, data[field.name], data)
        return data

    def __init__(__pydantic_self__, **data: Any) -> None:
        if "_results" in data:
            data = data["_results"]
            anchor = __pydantic_self__.get_anchor_element_from_model(model=__pydantic_self__)
            data = __pydantic_self__.filter_sparql(data, anchor=anchor[0])[0]
        data = __pydantic_self__.map_fields_data(data=data)
        data = __pydantic_self__.post_process_data(data=data)
        # if "label" in data:
        #     data["label"] = data["label"][0]
        super().__init__(**data)
