from django.contrib import admin
from .models import *

class TimestampedAdmin(admin.ModelAdmin):
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(Provider, TimestampedAdmin)
admin.site.register(Person, TimestampedAdmin)
admin.site.register(Concept, TimestampedAdmin)
admin.site.register(CareSite, TimestampedAdmin)
admin.site.register(Domain, TimestampedAdmin)
admin.site.register(Observation, TimestampedAdmin)
admin.site.register(Emergencymessage, TimestampedAdmin)
admin.site.register(DrugExposure, TimestampedAdmin)
# admin.site.register(Address, TimestampedAdmin)
# admin.site.register(LinkedProvider, TimestampedAdmin)
# admin.site.register(EmergencyProvider, TimestampedAdmin)
# admin.site.register(ProviderCareSite, TimestampedAdmin)
# admin.site.register(ProviderConcept, TimestampedAdmin)
admin.site.register(VisitOccurrence, TimestampedAdmin)
