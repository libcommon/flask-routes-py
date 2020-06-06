# flask-routes-py

## Overview

The Flask web framework provides the decorator [@app.route](https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.route)
to define handlers for routes, which is the recommended method for simple web apps. However, using this method requires
that route handlers be tied to a specific app, and can make it difficult to track/unit test routes for larger web apps.
`flask-routes-py` provides mixins for defining routes as classes with static (`classmethod`) handlers, with optional extras
like integrated request parameter parsing with [flask-reqparser-py](https://github.com/libcommon/flask-reqparser-py), and
automated route discovery and registration with [lc-registry](https://github.com/libcommon/registry-py).

## Installation

### Install from PyPi (preferred method)

```bash
pip install lc-flask-routes
pip install lc-flask-routes[reqparser]  # enable support for lc_flask_reqparser
pip install lc-flask-routes[registry]   # enable support for lc_registry
pip install lc-flask-routes[all]        # enable all options
```

### Install from GitHub with Pip

```bash
pip install git+https://github.com/libcommon/flask-routes-py.git@vx.x.x#egg=lc_flask_routes
```

where `x.x.x` is the version you want to download.

## Install by Manual Download

To download the source distribution and/or wheel files, navigate to
`https://github.com/libcommon/flask-routes-py/tree/releases/vx.x.x/dist`, where `x.x.x` is the version you want to install,
and download either via the UI or with a tool like wget. Then to install run:

```bash
pip install <downloaded file>
```

Do _not_ change the name of the file after downloading, as Pip requires a specific naming convention for installation files.

## Dependencies

`flask-routes-py` depends on, and is designed to work with, the 
[Flask framework](https://flask.palletsprojects.com/en/1.1.x/).  Optional dependencies also include
[flask-reqparser-py](https://github.com/libcommon/flask-reqparser-py) for integrated request parameter parsing, and
[lc-registry](https://github.com/libcommon/registry-py) for route auto-discovery. Only Python versions >= 3.6 are
officially supported.

## Getting Started

Define a base class that extends either the `BaseRouteMixin` or `BaseRouteWithParserMixin` class
(if installed with `[reqparser]` or `[all]` options) that all other route classes will extend. This class could
contain any helper methods or class variables needed by all routes, but should _not_ define the `ROUTE_MAP` class
variable.

```python
from typing import Any, Dict, Optional

import flask
from lc_flask_routes import (
    BaseRouteMixin,
    BaseRouteWithParserMixin,
    RouteResponse,
    WerkzeugLocalProxy
)
from lc_flask_reqparser import RequestParser


class BaseRoute(BaseRouteMixin):
    """Base route."""
    __slots__ = ()


class BaseParserRoute(BaseRouteWithParserMixin):
    """Base route with request parser."""
    __slots__ = ()

    @classmethod
    def gen_request_parser(cls) -> Optional[RequestParser]:
        return (RequestParser()
                .add_argument("base_argument_for_all_routes"))


class IndexRoute(BaseRoute):
    """Route: /
    Endpoint: "index"
    Description: Splash page
    """
    __slots__ = ()

    ROUTE_MAP = {"/": {"endpoint": "index", "methods": ["GET", "POST"]}}

    @classmethod
    def get(cls,
            app: WerkzeugLocalProxy,
            request: WerkzeugLocalProxy,
            session: WerkzeugLocalProxy,
            route_kwargs: Dict[str, Any]) -> RouteResponse:
        return "<h1>Splash Page</h1>"

    @classmethod
    def post(cls,
             app: WerkzeugLocalProxy,
             request: WerkzeugLocalProxy,
             session: WerkzeugLocalProxy,
             route_kwargs: Dict[str, Any]) -> RouteResponse:
        return flask.redirect(url_for("index"))


if __name__ == "__main__":
    app = flask.Flask(__name__)
    IndexRoute.register_route(app)
    app.run()
```

The `ROUTE_MAP` class variable should only be defined on non-base routes, and its structure mimics the parameters
for Flask's `@app.route` decorator, which really calls [add_url_rule](https://flask.palletsprojects.com/en/1.1.x/api/#flask.Flask.add_url_rule)
under the hood. Each key is a URI, and each corresponding value are the keyword arguments passed to `add_url_rule`. See Flask's documentation
for expectations and limitations of that function. `BaseRouteMixin` has a `register_route` method that accomplishes the same result as `@app.route`.
Each route class must be registered individually (unless using `RouteRegistryMixin` - see below).

If installed with the `[registry]` or `[all]` options, `flask-routes-py` also exposes a `RouteRegistryMixin` class to be used for auto-discovery
of route classes using metaprogramming. Define a Python `metaclass` that extends `RouteRegistryMixin`, then define a base class that uses this
`metaclass`.

```python
from abc import ABCMeta
from typing import Any, Dict

import flask
from lc_flask_routes import (
    BaseRouteMixin,
    BaseRouteWithParserMixin,
    RouteResponse,
    WerkzeugLocalProxy
)


class RouteRegistry(RouteRegistryMixin, ABCMeta):
    """Route registry."""
    __slots__ = ()

    _REGISTRY = dict()


class BaseRoute(BaseRouteMixin, metaclass=RouteRegistry):
    """Base route. Any child class will be registered in
    RouteRegistry's _REGISTRY class variable automatically
    (as long as it's in scope)."""


class IndexRoute(BaseRoute):
    """Route: /
    Endpoint: "index"
    Description: Splash page
    """
    __slots__ = ()

    ROUTE_MAP = {"/": {"endpoint": "index", "methods": ["GET"]}}

    @classmethod
    def get(cls,
            app: WerkzeugLocalProxy,
            request: WerkzeugLocalProxy,
            session: WerkzeugLocalProxy,
            route_kwargs: Dict[str, Any]) -> RouteResponse:
        return "<h1>Splash Page</h1>"


class LoginRoute(BaseRoute):
    """Route: /login
    Endpoint: "login"
    Description: Login workflow
    """
    __slots__ = ()

    ROUTE_MAP = {"/login": {"endpoint": "login", "methods": ["POST"]}}

    @classmethod
    def post(cls,
             app: WerkzeugLocalProxy,
             request: WerkzeugLocalProxy,
             session: WerkzeugLocalProxy,
             route_kwargs: Dict[str, Any]) -> RouteResponse:
        // Do some work to verify identity
        return flask.redirect(url_for("index"))


if __name__ == "__main__":
    app = flask.Flask(__name__)
    # Register IndexRoute and LoginRoute with app
    RouteRegistry.register_routes(app)
    app.run()
```

`RouteRegistryMixin` exposes two methods for registering routes with an app: `register_routes` and `register_routes_where`.
As shown above, `register_routes` will register all routes in the registry without any filtering, whereas `register_routes_where`
evaluates a provided predicate on reach route class before registering it. This could be useful, for example, if the same registry is being used
to initialize two different apps based on a class variable.

## Contributing/Suggestions

Contributions and suggestions are welcome! To make a feature request, report a bug, or otherwise comment on existing
functionality, please file an issue. For contributions please submit a PR, but make sure to lint, type-check, and test
your code before doing so. Thanks in advance!
