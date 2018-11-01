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


def test_name():
    a = schema({
        'type': 'dict'
    })

    assert a.name == '6b6218295eb1a7b2db98a916f8e27af8'

    b = schema({
        'type': 'dict'
    })

    assert a.name == b.name

    c = schema({
        'type': 'dict'
    }, name='dict')

    assert c.name == 'dict'

    c = schema({
        'type': 'dict'
    }, name='test.dict')

    assert c.name == 'test.dict'


def test_hash():
    s = schema({
        'type': 'dict'
    })

    assert s.get_hash() == '6b6218295eb1a7b2db98a916f8e27af8'
