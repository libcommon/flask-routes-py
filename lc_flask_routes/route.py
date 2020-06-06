## -*- coding: UTF-8 -*-
## route.py
##
## Copyright (c) 2020 libcommon
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.
# pylint: disable=W0613

import logging
import os
from typing import Any, ClassVar, Dict, Optional, Tuple, Union

import flask
from werkzeug.local import LocalProxy as WerkzeugLocalProxy
from werkzeug.wrappers import Response as WerkzeugResponse


__author__ = "libcommon"
logger = logging.getLogger(__name__)    # pylint: disable=invalid-name


RouteMap = Dict[str, Dict[str, Any]]
RouteResponseData = Union[WerkzeugResponse, Dict[str, Any], str]
RouteResponse = Union[Tuple[RouteResponseData, int], RouteResponseData]


class BaseRouteMixin:
    """Mixin for Flask routes intended to be replacement for
    using the typical @app.route decorator, and to be used with
    `RouteRegistryMixin` (though not required). Supports GET, POST, PUT, and DELETE
    HTTP methods out of the box, any other methods could be supported by a subclass.
    All handlers are classmethods, so each route class acts like a singleton
    (with no instance-level state).
    """
    __slots__ = ()

    # key-value pairs map to arguments for the flask.Flask.add_url_rule
    # see: https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.add_url_rule
    ROUTE_MAP: ClassVar[Optional[RouteMap]] = None

    @classmethod
    def register_route(cls, app: flask.Flask) -> None:
        """
        Args:
            app     => Flask app to register route(s) with
        Procedure:
            Register route(s) defined in cls.ROUTE_MAP with provided Flask app.
        Preconditions:
            N/A
        Raises:
            This function does not raise an exception, because the failure to register
            one route should not necessarily preclude registering other routes. Instead,
            it logs a WARNING for each route that fails.
        """
        # If ROUTE_MAP defined
        if cls.ROUTE_MAP:
            # For each route defined in ROUTE_MAP
            for route, route_options in cls.ROUTE_MAP.items():
                try:
                    # Ensure "view_func" key isn't defined in route_options
                    # Would conflict with setting view_func=cls.handle_request
                    if "view_func" in route_options:
                        raise KeyError("route options cannot contain \"view_func\" key")
                    # Add route with options to app, using cls.handle_request as route handler ("view_func")
                    app.add_url_rule(route, view_func=cls.handle_request, **route_options)
                except Exception as exc:
                    logger.warning("Failed to register handler for route {} ({})".format(route, exc))

    @classmethod
    def handle_request(cls, **route_kwargs) -> RouteResponse:
        """
        Args:
            route_kwargs    => arguments from variable rules
                               (see: https://flask.palletsprojects.com/en/1.1.x/quickstart/#variable-rules)
        Returns:
            Response from appropriate HTTP method handler.
        Preconditions:
            N/A
        Raises:
            TODO
        """
        # Get current app, request, and session
        app = flask.current_app
        request = flask.request
        request_method = request.method.lower()
        session = flask.session

        # If class doesn't have handler defined for HTTP method, return 405 response
        # This protects against a situation where an HTTP method is enabled in cls.ROUTE_MAP
        # but no associated handler is implemented.
        # see: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/405
        if not hasattr(cls, request_method):
            flask.abort(405)

        # Trigger handler for method
        return getattr(cls, request_method)(app, request, session, route_kwargs)

    @classmethod
    def get(cls,
            app: WerkzeugLocalProxy,
            request: WerkzeugLocalProxy,
            session: WerkzeugLocalProxy,
            route_kwargs: Dict[str, Any]) -> RouteResponse:
        """Handle GET requests to route(s)."""
        flask.abort(405)

    @classmethod
    def post(cls,
             app: WerkzeugLocalProxy,
             request: WerkzeugLocalProxy,
             session: WerkzeugLocalProxy,
             route_kwargs: Dict[str, Any]) -> RouteResponse:
        """Handle POST requests to route(s)."""
        flask.abort(405)

    @classmethod
    def put(cls,
            app: WerkzeugLocalProxy,
            request: WerkzeugLocalProxy,
            session: WerkzeugLocalProxy,
            route_kwargs: Dict[str, Any]) -> RouteResponse:
        """Handle PUT requests to route(s)."""
        flask.abort(405)

    @classmethod
    def delete(cls,
               app: WerkzeugLocalProxy,
               request: WerkzeugLocalProxy,
               session: WerkzeugLocalProxy,
               route_kwargs: Dict[str, Any]) -> RouteResponse:
        """Handle DELETE requests to route(s)."""
        flask.abort(405)


try:
    from lc_flask_reqparser import RequestParser


    class BaseRouteWithParserMixin(BaseRouteMixin):
        """Like `BaseRouteMixin`, but supports defining a
        `RequestParser` to parse GET, POST, or PUT parameters.
        """
        __slots__ = ()

        @classmethod
        def gen_request_parser(cls) -> Optional[RequestParser]:
            """
            Args:
                N/A
            Returns:
                Parser for URL parameters (GET) or request body (POST/PUT). Default
                implementation returns None.
            Preconditions:
                N/A
            Raises:
                N/A
            """
            return None

        @classmethod
        def handle_request(cls, **route_kwargs) -> RouteResponse:
            # Get current request and HTTP method
            request = flask.request
            request_method = request.method

            # Generate request parser
            parser = cls.gen_request_parser()
            # If request parser defined and HTTP method is GET, POST, or PUT
            if parser and request_method in {"GET", "POST", "PUT"}:
                try:
                    # Try to parse known request arguments
                    args, _ = parser.parse_args()
                except TypeError:
                    # Indicates invalid mimetype for POST/PUT request
                    # return 415 response ("Unsupported Media Type")
                    # see: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/415
                    flask.abort(415)
                except RuntimeError as exc:
                    # If error message indicates failed to parse
                    # request arguments, return 400 response ("Bad Request")
                    # see: RequestParser.error
                    if (exc.args and
                        isinstance(exc.args[0], str) and
                        exc.args[0].startswith("Failed to parse provided arguments")):
                        flask.abort(400)
                    # Otherwise, indicates outside of request context
                    # and should raise original exception
                    else:
                        raise

                # Merge parsed request arguments with route_kwargs
                # NOTE: request arguments will override route variable rules
                route_kwargs.update(dict(args._get_kwargs()))

            # Trigger handler from BaseRouteMixin with updated route_kwargs
            return super().handle_request(**route_kwargs)

except (ImportError, ModuleNotFoundError):
    pass


if os.environ.get("ENVIRONMENT") == "TEST":
    import unittest


    def gen_flask_app():
        """Generate test Flask app."""
        return flask.Flask(__name__)


    class BaseRoute(BaseRouteMixin):
        """Base route class."""
        __slots__ = ()


    class IndexRoute(BaseRoute):
        """Route: /
        Endpoint: "index"
        Description: Splash page
        """
        __slots__ = ()

        ROUTE_MAP = {
            "/": {"endpoint": "index_root", "methods": ["GET"]},
            "/index": {"endpoint": "index_index", "methods": ["GET", "PATCH"]},
        }

        @classmethod
        def get(cls,
                app: WerkzeugLocalProxy,
                request: WerkzeugLocalProxy,
                session: WerkzeugLocalProxy,
                route_kwargs: Dict[str, Any]) -> RouteResponse:
            return "<h1>Splash Page</h1>", 200


    class InvalidRoute(BaseRoute):
        """Route: /invalid
        Endpoint: "invalid"
        Description: Route with invalid ROUTE_MAP ("view_func")
        """
        __slots__ = ()

        ROUTE_MAP = {"/invalid": {
            "endpoint": "invalid",
            "methods": ["GET", "POST"],
            "view_func": lambda **kwargs: "<h1>Invalid route</h1>",
        }}


    class TestBaseRouteMixin(unittest.TestCase):
        """Tests for BaseRouteMixin."""

        def test_register_routes_url_map(self):
            """Test BaseRouteMixin.register_route to ensure each defined route
            gets registered with correct endpoint, rule (URI), and methods.
            """
            # Create Flask app
            app = gen_flask_app()

            # Register IndexRoute with app
            IndexRoute.register_route(app)
            # Ensure that "index" endpoint has rules "/" and "/index"
            # with proper methods (at least "GET")
            # NOTE: Flask will automatically implement OPTIONS and HEAD
            for route, route_options in IndexRoute.ROUTE_MAP.items():
                endpoint = route_options.get("endpoint")
                rule_list = app.url_map._rules_by_endpoint.get(endpoint)
                self.assertTrue((bool(rule_list) and
                                rule_list[0].rule == route and
                                "GET" in rule_list[0].methods))

        def test_register_routes_view_func_in_options(self):
            """Test that any ROUTE_MAP with the "view_func" key
            defined raises KeyError on route registration.
            """
            # Create Flask app
            app = gen_flask_app()

            # Attempt to register InvalidRoute, which should log WARNING
            # see: https://docs.python.org/3/library/unittest.html#unittest.TestCase.assertLogs
            with self.assertLogs(logger=__name__, level=logging.WARNING):
                InvalidRoute.register_route(app)

        def test_handle_request_method_not_implemented(self):
            """Test that HTTP 405 status code is returned if HTTP
            method supported in ROUTE_MAP but not implemented on route class.
            """
            # Create Flask app
            app = gen_flask_app()

            # Register IndexRoute with app
            IndexRoute.register_route(app)
            # Send PATCH request to index route "/" and ensure
            # HTTP 405 status code returned
            with app.test_client() as client:
                response = client.patch("/")
                self.assertEqual(405, response.status_code)

        def test_handle_request_proper_method(self):
            """Test that handle_request triggers correct handler
            based on request method.
            """
            # Create Flask app
            app = gen_flask_app()

            # Register IndexRoute with app
            IndexRoute.register_route(app)
            # Ensure response status code was 200 and
            # HTML matches `IndexRoute.get` HTML response
            with app.test_client() as client:
                response = client.get("/")
                self.assertEqual(200, response.status_code)
                self.assertEqual(b"<h1>Splash Page</h1>", response.data)


    try:
        class NoParserNoVRRoute(BaseRouteWithParserMixin):
            """Route: /
            Endpoint: "index"
            Description: Splash Page
            """
            __slots__ = ()

            ROUTE_MAP = {"/": {"endpoint": "index", "methods": ["GET"]}}

            @classmethod
            def get(cls,
                    app: WerkzeugLocalProxy,
                    request: WerkzeugLocalProxy,
                    session: WerkzeugLocalProxy,
                    route_kwargs: Dict[str, Any]) -> RouteResponse:
                return route_kwargs, 200


        class NoParserWithVRRoute(NoParserNoVRRoute):
            __slots__ = ()

            ROUTE_MAP = {"/person/<full_name>": {"endpoint": "search_person", "methods": ["GET"]}}


        class WithParserNoVRRoute(NoParserNoVRRoute):
            __slots__ = ()

            ROUTE_MAP = {"/location": {"endpoint": "search_location", "methods": ["GET", "DELETE", "POST"]}}

            @classmethod
            def gen_request_parser(cls) -> Optional[RequestParser]:
                return (RequestParser()
                        .add_argument("name", required=True)
                        .add_argument("age", type=int, required=True))

            @classmethod
            def post(cls,
                     app: WerkzeugLocalProxy,
                     request: WerkzeugLocalProxy,
                     session: WerkzeugLocalProxy,
                     route_kwargs: Dict[str, Any]) -> RouteResponse:
                return route_kwargs, 200

            @classmethod
            def delete(cls,
                       app: WerkzeugLocalProxy,
                       request: WerkzeugLocalProxy,
                       session: WerkzeugLocalProxy,
                       route_kwargs: Dict[str, Any]) -> RouteResponse:
                return route_kwargs, 200


        class WithParserWithVRRoute(NoParserNoVRRoute):
            __slots__ = ()

            ROUTE_MAP = {"/team/<team_name>": {"endpoint": "search_location", "methods": ["GET"]}}

            @classmethod
            def gen_request_parser(cls) -> Optional[RequestParser]:
                return (RequestParser()
                        .add_argument("team_name")
                        .add_argument("alias"))


        class TestBaseRouteWithParserMixin(unittest.TestCase):
            """Tests for BaseRouteWithParserMixin."""

            def test_handle_request_no_parser_no_route_kwargs(self):
                """Test that if no parser and no route variable rules
                defined, route_kwargs passed to handler are empty.
                """
                # Create Flask app
                app = gen_flask_app()

                # Register NoParserNoVRRoute with app
                NoParserNoVRRoute.register_route(app)
                # Ensure JSON response is empty
                with app.test_client() as client:
                    response = client.get("/")
                    self.assertEqual(dict(), response.get_json(cache=False))

            def test_handle_request_no_parser_route_kwargs(self):
                """Test that if no parser defined but do have route
                variable rules, route_kwargs only contains variable rule
                values.
                """
                # Create Flask app
                app = gen_flask_app()

                # Register NoParserWithVRRoute with app
                NoParserWithVRRoute.register_route(app)
                # Ensure response only contains "full_name" kwarg
                with app.test_client() as client:
                    response = client.get("/person/peter%20johnson")
                    self.assertEqual(dict(full_name="peter johnson"), response.get_json(cache=False))

            def test_handle_request_with_parser_wrong_method(self):
                """Test that if parser defined but HTTP method isn't
                GET, POST, or PUT, route_kwargs doesn't contain any parameters
                sent with request.
                """
                # Create Flask app
                app = gen_flask_app()

                # Register WithParserNoVRRoute with app
                WithParserNoVRRoute.register_route(app)
                # Ensure response is empty
                with app.test_client() as client:
                    response = client.delete("/location?name=Sports%20Arena&age=5")
                    self.assertEqual(dict(), response.get_json(cache=False))

            def test_handle_request_with_parser_invalid_mimetype(self):
                """Test that if parser defined and HTTP method is POST,
                but mimetype isn't JSON, response is 400.
                """
                # Create Flask app
                app = gen_flask_app()

                # Register WithParserNoVRRoute with app
                WithParserNoVRRoute.register_route(app)
                # Ensure response code is 400
                with app.test_client() as client:
                    response = client.post("/location",
                                           data="<element><child>Hello World</child></element>",
                                           mimetype="text/xml")
                    self.assertEqual(400, response.status_code)

            def test_handle_request_with_parser_invalid_argument(self):
                """Test that if parser defined and argument invalid (parser
                fails to parser arguments), response is 400.
                """
                # Create Flask app
                app = gen_flask_app()

                # Register WithParserNoVRRoute with app
                WithParserNoVRRoute.register_route(app)
                # Ensure response code is 400
                with app.test_client() as client:
                    response = client.post("/location",
                                           json=dict(name="Sports Arena", age="invalid"))
                    self.assertEqual(400, response.status_code)

            def test_handle_request_with_parser_merge_arguments(self):
                """Test that if parser defined and arguments are valid, but
                no route variable rules defined, route_kwargs only contain
                parser arguments.
                """
                # Create Flask app
                app = gen_flask_app()

                # Register WithParserNoVRRoute with app
                WithParserNoVRRoute.register_route(app)
                # Ensure response JSON matches request
                with app.test_client() as client:
                    response = client.post("/location",
                                           json=dict(name="Sports Arena", age="10"))
                    self.assertEqual(dict(name="Sports Arena", age=10), response.get_json())

            def test_handle_request_with_parser_merge_arguments_vrules(self):
                """Test that if parser defined and arguments are valid, and
                route variable rules defined, route_kwargs contains
                parser arguments where parsed argument(s) overwrite variable rules.
                """
                # Create Flask app
                app = gen_flask_app()

                # Register WithParserWithVRRoute with app
                WithParserWithVRRoute.register_route(app)
                # Ensure response contains "team_name" from URL parameter,
                # not route variable rule
                with app.test_client() as client:
                    response = client.get("/team/FC%20Barcelona?team_name=FC%20Milan")
                    self.assertEqual(dict(team_name="FC Milan", alias=None), response.get_json())

    except (ImportError, ModuleNotFoundError):
        pass
