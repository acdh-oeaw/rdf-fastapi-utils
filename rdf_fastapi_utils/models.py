from copy import deepcopy
import datetime
from typing import Any, Callable, List, Tuple
import typing
from pydantic import BaseModel, Field, HttpUrl, ValidationError, constr
from pydantic.fields import ModelField


def removeNullNoneEmpty(ob):
    l = {}
    check = False
    for k, v in ob.items():
        if isinstance(v, dict):
            x = removeNullNoneEmpty(v)
            if len(x.keys()) > 0:
                l[k] = x
            if x != v:
                check = True
        elif isinstance(v, list):
            p = []
            for c in v:
                if isinstance(c, dict):
                    x = removeNullNoneEmpty(c)
                    if len(x.keys()) > 0:
                        p.append(x)
                elif c is not None and c != "":
                    p.append(c)
            if len(p) > 0:
                l[k] = p
            if p != v:
                check = True
        elif v is not None and v != "":
            l[k] = v
    if check:
        l = removeNullNoneEmpty(l)
    return l


class FieldConfigurationRDF(BaseModel):
    """Configuration for how to use RDF data in the field"""

    path: constr(regex="^[a-zA-Z0-9\._]+$") | None = Field(
        None, description="RDF variable to use for populating the field"
    )
    anchor: bool = Field(False, description="Whether to use the RDF variable as an anchor")
    default_value: Any = Field(None, description="Default value to use when populating the field")
    callback_function: Callable | None = Field(
        None, description="Callback for postprocessing data from the RDF variable"
    )
    serialization_class_callback: Callable | None = Field(
        None,
        description="Callback function for deciding on the correct class for serialization. Function\
            gets two parameters: fields (array) and RDFData and needs to return a list of tuples with `(field, [data])`.",
    )
    default_dict_key: constr(regex="^[a-zA-Z0-9_]+$") | None = Field(
        None, desctiption="In a related field use this key as default"
    )
    encode_function: Callable | None = Field(
        None,
        description="Callback for encoding data from the RDF variable. E.g for base64 encoding of URIs.\
            The function gets only the value of the field passed and returns the encoded field.",
    )
    bypass_data_mapping: bool = Field(
        False,
        description="Wether to bypass the automated data mapping, e.g. to do it in a dedicated callback function.",
    )


class RDFUtilsModelBaseClass(BaseModel):
    """Base class for models that use RDF data"""

    class Config:
        RDF_utils_catch_errors = False
        RDF_utils_error_field_name = "errors"
        # RDF_utils_move_errors_to_top = False FIXME: add again when #3 is resolved

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
            lst_unique_vals = set([x[anchor] for x in data if anchor in x])
            res_fin_anchor = []
            for item in lst_unique_vals:
                add_vals = []
                res1 = {}
                for i2 in list(filter(lambda d: d[anchor] == item, [x for x in data if anchor in x])):
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
        if hasattr(model, "__fields__"):
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
        if not hasattr(model, "__fields__"):
            return []
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
                # res[field.name] = data
                anchor = self.get_anchor_element_from_model(model=field.type_)
                if "_additional_values" in data:
                    if anchor is None and path in data["_additional_values"]:
                        res[field.name] = data["_additional_values"][path]
                res[field.name] = self.filter_sparql(
                    data=data["_additional_values"] if "_additional_values" in data else data,
                    # data=data,
                    anchor=anchor[0] if anchor is not None else None,
                    list_of_keys=self.get_rdf_variables_from_model(model=field.type_),
                )
                continue
            if (
                hasattr(field.type_, "__fields__")
                or hasattr(field.type_, "__args__")
                and not getattr(field.field_info.extra.get("rdfconfig"), "bypass_data_mapping", False)
            ):  # FIXME: this test doesnt catch all the options
                scallback_attr = getattr(field.field_info.extra.get("rdfconfig"), "serialization_class_callback", None)
                default_dict_key = getattr(field.field_info.extra.get("rdfconfig"), "default_dict_key", None)
                if scallback_attr is not None:
                    res[field.name] = []
                    if not isinstance(data[path], list):
                        data[path] = [data[path]]
                    # for ent in data[path]:
                    cb1 = scallback_attr(field, data[path])
                    for cb in cb1:
                        anchor = self.get_anchor_element_from_model(model=cb[0])
                        rdf_data = self.filter_sparql(
                            data=cb[1],
                            anchor=anchor[0],
                            list_of_keys=self.get_rdf_variables_from_model(model=cb[0]),
                        )
                        res[field.name].extend([cb[0](**ent) for ent in rdf_data])
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
                elif field.sub_fields is None:
                    anchor = self.get_anchor_element_from_model(model=field.type_)
                    res[field.name] = self.filter_sparql(
                        # data=data["_additional_values"] if "_additional_values" in data else data,
                        data=data,
                        anchor=anchor[0] if anchor is not None else None,
                        list_of_keys=self.get_rdf_variables_from_model(model=field.type_),
                    )[0]
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
                if data[field.name] is not None:
                    data[field.name] = cb(field, data[field.name], data)
        return data

    def encode_data(self, data: dict) -> dict:

        for field in self.__fields__.values():
            cb = getattr(field.field_info.extra.get("rdfconfig"), "encode_function", None)
            if cb is not None and field.name in data:
                if data[field.name] is not None:
                    data[field.name] = cb(data[field.name])
        return data

    def __init__(__pydantic_self__, **data: Any) -> None:
        if "_results" in data:
            data = data["_results"]
            anchor = __pydantic_self__.get_anchor_element_from_model(model=__pydantic_self__)
            data = __pydantic_self__.filter_sparql(
                data,
                anchor=anchor[0],
                list_of_keys=__pydantic_self__.get_rdf_variables_from_model(model=__pydantic_self__),
            )[0]
        sort_key = getattr(__pydantic_self__.Config, "sort_key", None)
        if sort_key is not None:
            original_order = []
            for item in data[sort_key["object list"]]:
                if item[sort_key["original key"]] not in original_order:
                    original_order.append(item[sort_key["original key"]])
        data = __pydantic_self__.map_fields_data(data=data)
        data = __pydantic_self__.post_process_data(data=data)
        data = __pydantic_self__.encode_data(data=data)
        if sort_key is not None:
            new_data = []
            for order_item in original_order:
                for item in data[sort_key["object list"]]:
                    if item[sort_key["original key"]] == order_item:
                        new_data.append(item)
            data[sort_key["object list"]] = new_data

        # if __pydantic_self__.__class__.__name__ == "Entity":
        #     if "gender" in data:
        #         if isinstance(data["gender"], list):
        #             data["gender"] = data["gender"][0]
        # if "label" in data:
        #     data["label"] = data["label"][0]
        if __pydantic_self__.Config.RDF_utils_catch_errors:
            try:
                super().__init__(**data)
            except ValidationError as e:
                print("Error in model", __pydantic_self__.__class__.__name__, e)
                data["_error"] = e
                data_copy = deepcopy(data)
                for err in e.errors():
                    c_back = list(err["loc"])
                    while len(c_back) > 0:
                        d1 = data_copy
                        for val in c_back[:-1]:
                            if val in d1 or (isinstance(d1, list) and val < len(d1)):
                                d1 = d1[val]
                            else:
                                break
                        try:
                            error_key = __pydantic_self__.Config.RDF_utils_error_field_name
                            prev_error = None
                            if isinstance(d1[c_back[-1]], dict) and error_key in d1[c_back[-1]]:
                                prev_error = d1[c_back[-1]][error_key]
                            d1[c_back[-1]] = None
                            if data_copy[error_key] is None:
                                data_copy[error_key] = []
                            if str(e).replace("\n ", "; ").replace("\n", "; ") not in data_copy[error_key]:
                                data_copy[error_key].append(str(e).replace("\n ", "; ").replace("\n", "; "))
                            if prev_error is not None:
                                for err2 in prev_error:
                                    if err2 not in data_copy[error_key]:
                                        data_copy[error_key].append(err2)
                            break
                        except (KeyError, IndexError):
                            if len(c_back) == 1:
                                break
                            del c_back[-1]
                data_copy = removeNullNoneEmpty(data_copy)
                super().__init__(**data_copy)
        else:
            super().__init__(**data)
