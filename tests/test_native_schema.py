from splendor.schema.native import system, schema

def test_dict():
    s = schema({
        'type': 'dict',
        'propertyNames': {'pattern': 'attr-.*'}
    })

    s.validate([
        ('attr-1', 1),
        ('attr-2', 2)
    ])


def test_instance_of():
    class A:
        def __init__(self, **props):
            self.__dict__.update(props)

    s = schema({
        'instance_of': A
    })

    a = s({'name': 'bob'})
    assert a.name == 'bob'
    assert isinstance(a, A)

    s = schema({
        'items': {'instance_of': A}
    })

    eys = s([{'name': 'first'}, A(name='second')])

    assert eys[0].name == 'first'
    assert eys[1].name == 'second'

    for obj in eys:
        assert isinstance(obj, A)
