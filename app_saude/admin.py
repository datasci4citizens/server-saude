from django.contrib import admin
from .models import *

admin.site.register(Provider)
admin.site.register(Person)
admin.site.register(Concept)
admin.site.register(CareSite)
admin.site.register(Domain)
admin.site.register(Observation)
admin.site.register(Emergencymessage)
admin.site.register(DrugExposure)
admin.site.register(Address)
admin.site.register(LinkedProvider)
admin.site.register(EmergencyProvider)
admin.site.register(ProviderCareSite)
admin.site.register(ProviderConcept)
admin.site.register(VisitOccurrence)
