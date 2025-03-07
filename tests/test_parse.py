from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from enum import IntEnum
import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Text
from typing import Union

import dataconf
from dataconf import load
from dataconf import loads
from dataconf.exceptions import AmbiguousSubclassException
from dataconf.exceptions import MalformedConfigException
from dataconf.exceptions import MissingTypeException
from dataconf.exceptions import ParseException
from dataconf.exceptions import TypeConfigException
from dataconf.exceptions import UnexpectedKeysException
from dataconf.main import file
from dataconf.main import url
from dateutil.relativedelta import relativedelta
import pytest
from pytest_httpserver import HTTPServer
from tests.conftest import file_handler

PARENT_DIR = os.path.normpath(
    os.path.dirname(os.path.realpath(__file__)) + os.sep + os.pardir
)


class InputType:
    pass


@dataclass(init=True, repr=True)
class StringImpl(InputType):
    name: Text
    age: Text

    def test_method(self):
        return f"{self.name} is {self.age} years old."

    def test_complex(self):
        return int(self.age) * 3


@dataclass(init=True, repr=True)
class IntImpl(InputType):
    area_code: int
    phone_num: Text

    def test_method(self):
        return f"The area code for {self.phone_num} is {str(self.area_code)}"

    def test_complex(self):
        return self.area_code - 10


class AmbigImplBase:
    pass


@dataclass(init=True, repr=True)
class AmbigImplOne(AmbigImplBase):
    bar: str


@dataclass(init=True, repr=True)
class AmbigImplTwo(AmbigImplBase):
    bar: str


class TestParser:
    def test_simple(self) -> None:
        @dataclass
        class A:
            a: Text

        conf = """
        a = test
        """
        assert loads(conf, A) == A(a="test")

    def test_relativedelta(self) -> None:
        @dataclass
        class A:
            a: relativedelta

        conf = """
        a = 2d
        """
        assert loads(conf, A) == A(a=relativedelta(days=2))

    def test_list(self) -> None:
        @dataclass
        class A:
            a: List[Text]

        conf = """
        a = [
            test
        ]
        """
        assert loads(conf, A) == A(a=["test"])

    def test_boolean(self) -> None:
        @dataclass
        class A:
            a: bool

        conf = """
        a = false
        """
        assert loads(conf, A) == A(a=False)

    def test_dict(self) -> None:
        @dataclass
        class A:
            a: Dict[Text, Text]

        conf = """
        a {
            b = test
        }
        """
        assert loads(conf, A) == A(a={"b": "test"})

    def test_nested(self) -> None:
        @dataclass
        class B:
            a: Text

        @dataclass
        class A:
            b: B

        conf = """
        b {
            a = test
        }
        """
        assert loads(conf, A) == A(b=B(a="test"))

    def test_union(self) -> None:
        @dataclass
        class B:
            a: Text

        @dataclass
        class A:
            b: Union[B, Text]

        conf = """
        b {
            a = test
        }
        """
        assert loads(conf, A) == A(b=B(a="test"))

        conf = """
        b = test
        """
        assert loads(conf, A) == A(b="test")

    def test_optional(self) -> None:
        @dataclass
        class A:
            b: Optional[Text] = None

        conf = ""
        assert loads(conf, A) == A(b=None)

        conf = """
        b = test
        """
        assert loads(conf, A) == A(b="test")

    def test_enum(self) -> None:
        class Color(Enum):
            RED = 1
            GREEN = 2
            BLUE = 3

        @dataclass
        class A:
            b: Color

        conf_name = """
        b = RED
        """
        assert loads(conf_name, A) == A(b=Color.RED)

        conf_value = """
        b = 2
        """
        assert loads(conf_value, A) == A(b=Color.GREEN)

    def test_int_num(self) -> None:
        class IntColor(IntEnum):
            RED = 1
            GREEN = 2
            BLUE = 3

        @dataclass
        class A:
            b: IntColor

        conf_name = """
        b = RED
        """
        assert loads(conf_name, A) == A(b=IntColor.RED)

        conf_value = """
        b = 2
        """
        assert loads(conf_value, A) == A(b=IntColor.GREEN)

    def test_datetime(self) -> None:
        @dataclass
        class A:
            b: datetime

        conf = """
        b = "1997-07-16T19:20:07+01:00"
        """
        assert loads(conf, A) == A(
            b=datetime(1997, 7, 16, 18, 20, 7, tzinfo=timezone.utc)
        )

    def test_bad_datetime(self) -> None:
        @dataclass
        class A:
            b: datetime

        conf = """
        b = "1997-07-16 19:20:0701:00"
        """
        with pytest.raises(ParseException):
            assert loads(conf, A)

    def test_optional_with_default(self) -> None:
        @dataclass
        class A:
            b: Optional[Text]

        conf = ""
        assert loads(conf, A) == A(b=None)

        conf = """
        b = test
        """
        assert loads(conf, A) == A(b="test")

    def test_empty_list(self) -> None:
        @dataclass
        class A:
            b: List[Text] = field(default_factory=list)

        conf = ""
        assert loads(conf, A) == A(b=[])

    def test_json(self) -> None:
        @dataclass
        class A:
            b: Text

        conf = """
        {
            "b": "c"
        }
        """
        assert loads(conf, A) == A(b="c")

    def test_default_value(self) -> None:
        @dataclass
        class A:
            b: Text = "c"

        assert loads("", A) == A(b="c")

    def test_root_dict(self) -> None:
        conf = """
        b: c
        """
        assert loads(conf, Dict[Text, Text]) == dict(b="c")

    def test_missing_type(self) -> None:
        with pytest.raises(MissingTypeException):
            loads("", Dict)

        with pytest.raises(MissingTypeException):
            loads("", List)

    def test_missing_field(self) -> None:
        @dataclass
        class A:
            b: Text

        conf = """
        {
            "typo": "c"
        }
        """
        with pytest.raises(MalformedConfigException):
            assert loads(conf, A) == A(b="c")

    def test_misformat(self) -> None:
        conf = """
        b {}
        c {
            f {
        }
        d {}
        }
        """

        @dataclass
        class Clazz:
            f: Dict[Text, Text] = field(default_factory=dict)

        with pytest.raises(UnexpectedKeysException):
            loads(conf, Dict[Text, Clazz])

    def test_ignore_unexpected(self) -> None:
        conf = """
        a = "hello"
        b = "world"
        """

        @dataclass
        class A:
            a: Text

        with pytest.raises(UnexpectedKeysException):
            loads(conf, A)

        assert loads(conf, A, ignore_unexpected=True) == A(a="hello")

    def test_complex_hocon(self) -> None:
        @dataclass
        class Conn:
            host: Text
            port: int
            ssl: Optional[Dict[Text, Text]] = field(default_factory=dict)

        @dataclass
        class Base:
            data_root: Text
            pipeline_name: Text
            data_type: Text
            production: bool
            conn: Optional[Conn] = None
            data_split: Optional[Dict[Text, int]] = None
            tfx_root: Optional[Text] = None
            metadata_root: Optional[Text] = None
            beam_args: Optional[List[Text]] = field(
                default_factory=lambda: [
                    "--direct_running_mode=multi_processing",
                    "--direct_num_workers=0",
                ]
            )

        conf = load(os.path.join(PARENT_DIR, "confs", "complex.hocon"), Base)

        assert conf == Base(
            data_root="/some/path/here",
            pipeline_name="Penguin-Config",
            data_type="tfrecord",
            production=True,
            conn=Conn(host="test.server.io", port=443),
        )

    def test_traits_string_impl(self) -> None:
        @dataclass
        class Base:
            location: Text
            input_source: InputType

        str_conf = """
        {
            location: Europe
            input_source {
                name: Thailand
                age: "12"
            }
        }
        """

        conf = loads(str_conf, Base)
        assert conf == Base(
            location="Europe",
            input_source=StringImpl(name="Thailand", age="12"),
        )
        assert conf.input_source.test_method() == "Thailand is 12 years old."
        assert conf.input_source.test_complex() == 36

    def test_traits_int_impl(self) -> None:
        @dataclass
        class Base:
            location: Text
            input_source: InputType

        str_conf = """
        {
            location: Europe
            input_source {
                area_code: 94
                phone_num: "1234567"
            }
        }
        """

        conf = loads(str_conf, Base)
        assert conf == Base(
            location="Europe",
            input_source=IntImpl(area_code=94, phone_num="1234567"),
        )
        assert conf.input_source.test_method() == "The area code for 1234567 is 94"
        assert conf.input_source.test_complex() == 84

    def test_traits_failure(self) -> None:
        @dataclass
        class Base:
            location: Text
            input_source: InputType

        str_conf = """
        {
            location: Europe
            input_source {
                name: Thailand
                age: "12"
                city: Paris
            }
        }
        """

        with pytest.raises(TypeConfigException) as e:
            loads(str_conf, Base)

        assert e.value.args[0] == (
            "expected type <class 'tests.test_parse.InputType'> at .input_source, failed subclasses:\n"
            "- expected type <class 'tests.test_parse.IntImpl'> at .input_source, no area_code found in dataclass\n"
            "- unexpected key(s) \"city\" detected for type <class 'tests.test_parse.StringImpl'> at .input_source"
        )

    def test_traits_ambiguous(self) -> None:
        @dataclass
        class Base:
            a: Text
            foo: AmbigImplBase

        str_conf = """
        {
            a: Europe
            foo {
                bar: Baz
            }
        }
        """
        with pytest.raises(AmbiguousSubclassException) as e:
            loads(str_conf, Base)

        assert e.value.args[0] == (
            "multiple subtypes of <class 'tests.test_parse.AmbigImplBase'> matched at .foo, use '_type' to disambiguate:\n"
            "- AmbigImplOne\n"
            "- AmbigImplTwo"
        )

        unambig_str_conf = """
        {
            a: Europe
            foo {
                _type: AmbigImplTwo
                bar: Baz
            }
        }
        """
        conf = loads(unambig_str_conf, Base)
        assert isinstance(conf.foo, AmbigImplTwo)

    def test_any(self) -> None:
        @dataclass
        class Base:
            foo: Any

        conf = """
        {
            foo: [1, 2]
        }
        """
        assert loads(conf, Base).foo == [1, 2]

        conf = """
        {
            foo: {a: 1}
        }
        """
        assert loads(conf, Base).foo == {"a": 1}

        conf = """
        {
            foo: 1
        }
        """
        assert loads(conf, Base).foo == 1

        conf = """
        {
            foo: test
        }
        """
        assert loads(conf, Base).foo == "test"

    def test_nested_any(self) -> None:
        @dataclass
        class Base:
            foo: Dict[str, Any]

        conf = """
        {
            foo: {a: 1}
        }
        """
        assert loads(conf, Base).foo == {"a": 1}

        conf = """
        {
            foo: {a: {b: c}}
        }
        """
        assert loads(conf, Base).foo == {"a": {"b": "c"}}

        conf = """
        {
            foo: {a: {b: {d: 1}}}
        }
        """
        assert loads(conf, Base).foo == {"a": {"b": {"d": 1}}}

        conf = """
        {
            foo: {a: {b: [c, {d: 1}]}}
        }
        """
        assert loads(conf, Base).foo == {"a": {"b": ["c", {"d": 1}]}}

    def test_list_any(self) -> None:
        @dataclass
        class Base:
            foo: List[Any]

        conf = """
        {
            foo: [
                1
                "b"
            ]
        }
        """
        assert loads(conf, Base).foo == [1, "b"]

        conf = """
        {
            foo: [
                {a: 1}
                [
                    2
                ]
            ]
        }
        """
        assert loads(conf, Base).foo == [{"a": 1}, [2]]

    def test_yaml(self) -> None:
        @dataclass
        class B:
            c: Text

        @dataclass
        class A:
            b: B

        conf = """
        b:
          c: test
        """
        assert loads(conf, A, loader=dataconf.YAML) == A(b=B(c="test"))

    def test_yaml_file(self) -> None:
        @dataclass
        class A:
            hello: Text
            foo: List[str]

        assert file("confs/simple.yaml", A) == A(hello="bonjour", foo=["bar"])

    def test_yaml_url(self, httpserver: HTTPServer) -> None:
        @dataclass
        class A:
            hello: Text
            foo: List[str]

        httpserver.expect_request("/simple.yaml").respond_with_handler(
            file_handler("confs/simple.yaml")
        )

        assert url(
            httpserver.url_for("/simple.yaml"),
            A,
        ) == A(hello="bonjour", foo=["bar"])

    def test_json_file(self) -> None:
        @dataclass
        class A:
            hello: Text
            foo: List[str]

        assert file("confs/simple.json", A) == A(hello="bonjour", foo=["bar"])

    def test_json_url(self, httpserver: HTTPServer) -> None:
        @dataclass
        class A:
            hello: Text
            foo: List[str]

        httpserver.expect_request("/simple.json").respond_with_handler(
            file_handler("confs/simple.json")
        )

        assert url(httpserver.url_for("/simple.json"), A) == A(
            hello="bonjour", foo=["bar"]
        )
