Versioning
============

Versioning a service is an important part of its life cycle.  Fundamentally a service API is a 
contract between its developers and its users, with expectations of change being limited.  On one 
hand, people want to use new features, on the other no one wants to find their application suddenly 
break when a service adds a bunch of backwards incompatible upgrades. 

Feature Branching
-----------------

One of the design goals of Splendor is to foster APIs that are able to deliver multiple versions
easily.  The suggested way to do that is through feature branching.  Normally, we think of 
versioning as something that is contained within your source code.  But that won't actually work if
you are trying to support multiple versions at the same time.

So we use a strategy called "Feature Branching", which basically comes down to saving versions of
our features to sit alongside each other.

For example, let's create ``GreetingServiceV1`` and ``GreetingServiceV2``, and we'll see the same
greetings endpoint defined twice::

    def hello_v1():
        return "Hello World"

    def hello_v2():
        target = request.args.get('target', 'World')
        return {
            'greeting': f"Hello {target}",
            'target': target
        }

    class GreetingServiceV1(Api):
        info = {'title': 'Greeting API', 'version': '1.0.1'}
        paths = {
            '/hello': hello_v1
        }

    class GreetingServiceV2(Api):
        info = {'title': 'Greeting API', 'version': '2.0.0'}
        paths = {
            '/hello': hello_v2
        }

As you can see here, we've defined two versions of the `/hello` endpoint.  The versions of our API
differ only by the version of hello they use.  The two versions can sit next to each other, or you
could separate them into different files.


Version Iteration
----------------------
Since we now have feature branching in place, a natural pattern emerges in regards to iteration. 
Our latest version is always a "dev" version (/dev), prone to change, guaranteeing nothing.  It is
the focus of innovation, new features.  When we are ready to "release" it, we build our documentation,
achieve a sufficient test coverage, and then tell our users it's done (/v1).  After we release it, 
the version becomes locked, only bug fixes or limited features.  Then we create a new version for
development, and repeat.  Often we'll find we only added features, and did not remove or alter
any existing features.  In which case we can replace our previous version (/v1).  Or if our
functionality changes enough we can release a new one (/v2).

