from splendor.schema import fields

class Pet(fields.Schematic):
    name = fields.String(min_length=3, max_length=50)
    status = fields.Enum(['available', 'pending', 'sold'],
                            default='available')

mittens = Pet(name="Mr. Mittens", status="pending")
mittens.status = 'sold'
print(mittens.name, "is now", mittens.status)

import json
print( json.dumps(mittens.marshal_as('json')) )

print(Pet.__schema__)