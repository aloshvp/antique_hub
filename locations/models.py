from django.db import models


class State(models.Model):
    """
    State master model representing geographical states.
    From synopsis: State(stateid, state)
    """
    stateid = models.AutoField(primary_key=True)
    state = models.CharField(max_length=100, unique=True, verbose_name="State Name")

    class Meta:
        db_table = 'state'
        ordering = ['state']
        verbose_name = 'State'
        verbose_name_plural = 'States'

    def __str__(self):
        return self.state


class District(models.Model):
    """
    District model linked to State.
    From synopsis: District(distid, dist, state FK)
    """
    distid = models.AutoField(primary_key=True)
    dist = models.CharField(max_length=100, verbose_name="District Name")
    state = models.ForeignKey(
        State,
        on_delete=models.CASCADE,
        related_name='districts',
        verbose_name="State"
    )

    class Meta:
        db_table = 'district'
        ordering = ['state__state', 'dist']
        unique_together = ('state', 'dist')
        verbose_name = 'District'
        verbose_name_plural = 'Districts'

    def __str__(self):
        return f"{self.dist}, {self.state.state}"


class Location(models.Model):
    """
    Location model linked to District.
    From synopsis: Location(locid, locname, district FK)
    """
    locid = models.AutoField(primary_key=True)
    locname = models.CharField(max_length=150, verbose_name="Location Name")
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name='locations',
        verbose_name="District"
    )

    class Meta:
        db_table = 'location'
        ordering = ['district__dist', 'locname']
        unique_together = ('district', 'locname')
        verbose_name = 'Location'
        verbose_name_plural = 'Locations'

    def __str__(self):
        return f"{self.locname} ({self.district.dist})"
