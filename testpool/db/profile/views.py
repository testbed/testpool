# (c) 2016 Mark Hamilton, <mark.lee.hamilton@gmail.com>
#
# This file is part of testpool
#
# Testbed is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Testbed is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Testdb.  If not, see <http://www.gnu.org/licenses/>.
from django.shortcuts import render_to_response
from testpooldb import models

class ProfileView(object):
    def __init__(self, profile):
        """Contruct a product view. """
        self.name = profile.name
        self.vm_max = profile.vm_max
        self.vm_free = 0
        self.vm_reserved = 0
        self.vm_released = 0

        for item in models.VM.objects.filter(profile=profile):
            if item.status == models.VM.RESERVED:
                self.vm_reserved += 1
            elif item.status == models.VM.RELEASED:
                self.vm_released += 1
            elif item.status == models.VM.FREE:
                self.vm_free += 1

def index(_):
    """ Summarize product information. """

    profiles = models.Profile.objects.all()
    profiles = [ProfileView(item) for item in profiles]

    html_data = {"profiles": profiles}
    return render_to_response("profile/index.html", html_data)
