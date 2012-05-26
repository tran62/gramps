# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2009         Douglas S. Blank <doug.blank@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# $Id: utils.py 19637 2012-05-24 17:22:14Z dsblank $
#

""" Views for Person, Name, and Surname """

## Gramps Modules
from webapp.utils import _, boolean, update_last_changed
from webapp.grampsdb.models import Person, Name, Surname
from webapp.grampsdb.forms import *
from webapp.libdjango import DjangoInterface

## Django Modules
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.template import Context, RequestContext

## Globals
dji = DjangoInterface()

## Functions
def check_order(request, person):
    """
    Check for proper ordering 1..., and for a preferred name.
    """
    order = 1
    preferred = False
    for name in person.name_set.all().order_by("order"):
        if name.preferred:
            preferred = True
        if name.order != order:
            name.order = order
            update_last_changed(name, request.user.username)
            name.save()
        order += 1
    if not preferred:
        name = person.name_set.get(order=1)
        name.preferred = True
        update_last_changed(name, request.user.username)
        name.save()

def check_primary(surname, surnames):
    """
    Check for a proper primary surname.
    """
    if surname.primary:
        # then all rest should not be:
        for s in surnames:
            if s.primary:
                s.primary = False
                s.save()
    else:
        # then one of them should be
        ok = False
        for s in surnames:
            if s.id != surname.id:
                if s.primary:
                    ok = True
                    break
                else:
                    s.primary = False
                    s.save()
                    ok = True
                    break
        if not ok:
            surname.primary = True

def check_preferred(name, person):
    """
    Check for a proper preferred name.
    """
    names = []
    if person:
        names = person.name_set.all()
    if name.preferred:
        # then all reast should not be:
        for s in names:
            if s.preferred and s.id != name.id:
                s.preferred = False
                update_last_changed(s, request.user.username)
                s.save()
    else:
        # then one of them should be
        ok = False
        for s in names:
            if s.id != name.id:
                if s.preferred:
                    ok = True
                    break
                else:
                    s.preferred = False
                    update_last_changed(s, request.user.username)
                    s.save()
                    ok = True
                    break
        if not ok:
            name.preferred = True

def process_surname(request, handle, order, sorder, action="view"):
    #import pdb; pdb.set_trace()
    # /sdjhgsdjhdhgsd/name/1/surname/1  (view)
    # /sdjhgsdjhdhgsd/name/1/surname/add
    # /sdjhgsdjhdhgsd/name/1/surname/2/[edit|view|add|delete]

    if sorder == "add":
        action = "add"
    if request.POST.has_key("action"):
        action = request.POST.get("action")

    person = Person.objects.get(handle=handle)
    name = person.name_set.get(order=order)

    if action in ["view", "edit"]:
        surname = name.surname_set.get(order=sorder)
        if action == "edit":
            surname.prefix = make_empty(True, surname.prefix, " prefix ")
    elif action in ["delete"]:
        surnames = name.surname_set.all().order_by("order")
        if len(surnames) > 1:
            neworder = 1
            for surname in surnames:
                if surname.order != neworder:
                    surname.order = neworder
                    surname.save()
                    neworder += 1
                elif surname.order == int(sorder):
                    surname.delete()
                else:
                    neworder += 1
        else:
            request.user.message_set.create(message="You can't delete the only surname")
        return redirect("/person/%s/name/%s" % (person.handle, name.order))
    elif action in ["add"]:
        surname = Surname(name=name, primary=False, 
                          name_origin_type=NameOriginType.objects.get(val=NameOriginType._DEFAULT[0]))
        surname.prefix = make_empty(True, surname.prefix, " prefix ")
    elif action == "create":
        import pdb; pdb.set_trace()

        surnames = name.surname_set.all().order_by("order")
        sorder = 1
        for surname in surnames:
            sorder += 1
        surname = Surname(name=name, primary=True, 
                          name_origin_type=NameOriginType.objects.get(val=NameOriginType._DEFAULT[0]),
                          order=sorder)
        sf = SurnameForm(request.POST, instance=surname)
        sf.model = surname
        if sf.is_valid():
            surname.prefix = ssf.cleaned_data["prefix"] if sf.cleaned_data["prefix"] != " prefix " else ""
            surname = sf.save(commit=False)
            check_primary(surname, surnames)
            surname.save()
            return redirect("/person/%s/name/%s/surname/%s" % 
                            (person.handle, name.order, sorder))
        action = "add"
        surname.prefix = make_empty(True, surname.prefix, " prefix ")
    elif action == "save":
        surname = name.surname_set.get(order=sorder)
        sf = SurnameForm(request.POST, instance=surname)
        sf.model = surname
        if sf.is_valid():
            surname.prefix = ssf.cleaned_data["prefix"] if sf.cleaned_data["prefix"] != " prefix " else ""
            surname = sf.save(commit=False)
            check_primary(surname, name.surname_set.all().exclude(order=surname.order))
            surname.save()
            return redirect("/person/%s/name/%s/surname/%s" % 
                            (person.handle, name.order, sorder))
        action = "edit"
        surname.prefix = make_empty(True, surname.prefix, " prefix ")
        # else, edit again
    else:
        raise

    sf = SurnameForm(instance=surname)
    sf.model = surname

    context = RequestContext(request)
    context["action"] = action
    context["tview"] = _("Surname")
    context["handle"] = handle
    context["id"] = id
    context["person"] = person
    context["object"] = person
    context["surnameform"] = sf
    context["order"] = name.order
    context["sorder"] = sorder
    view_template = 'view_surname_detail.html'
    return render_to_response(view_template, context)

def process_name(request, handle, order, action="view"):
    if order == "add":
        action = "add"
    if request.POST.has_key("action"):
        action = request.POST.get("action")
    ### Process action:
    if action == "view":
        pf, nf, sf, person = get_person_forms(handle, order=order)
        name = nf.model
    elif action == "edit":
        pf, nf, sf, person = get_person_forms(handle, order=order)
        name = nf.model
    elif action == "delete":
        person = Person.objects.get(handle=handle)
        name = person.name_set.filter(order=order)
        names = person.name_set.all()
        if len(names) > 1:
            name.delete()
            check_order(request, person)
        else:
            request.user.message_set.create(message = "Can't delete only name.")
        return redirect("/person/%s" % person.handle)
    elif action == "add": # add name
        person = Person.objects.get(handle=handle)
        name = Name(person=person, 
                    preferred=False,
                    display_as=NameFormatType.objects.get(val=NameFormatType._DEFAULT[0]), 
                    sort_as=NameFormatType.objects.get(val=NameFormatType._DEFAULT[0]), 
                    name_type=NameType.objects.get(val=NameType._DEFAULT[0]))
        nf = NameForm(instance=name)
        nf.model = name
        surname = Surname(name=name, 
                          primary=True, 
                          order=1,
                          name_origin_type=NameOriginType.objects.get(val=NameOriginType._DEFAULT[0]))
        sf = SurnameForm(request.POST, instance=surname)
    elif action == "create":
        # make new data
        person = Person.objects.get(handle=handle)
        name = Name(preferred=False)
        next_order = max([name.order for name in person.name_set.all()]) + 1
        surname = Surname(name=name, 
                          primary=True, 
                          order=next_order, 
                          name_origin_type=NameOriginType.objects.get(val=NameOriginType._DEFAULT[0]))
        # combine with user data:
        nf = NameForm(request.POST, instance=name)
        name.id = None # FIXME: why did this get set to an existing name? Should be new.
        name.preferred = False
        nf.model = name
        sf = SurnameForm(request.POST, instance=surname)
        sf.model = surname
        if nf.is_valid() and sf.is_valid():
            # name.preferred and surname.primary get set False in the above is_valid()
            # person = pf.save()
            # Process data:
            name = nf.save(commit=False)
            name.person = person
            update_last_changed(name, request.user.username)
            # Manually set any data:
            name.suffix = nf.cleaned_data["suffix"] if nf.cleaned_data["suffix"] != " suffix " else ""
            name.preferred = False # FIXME: why is this False?
            name.order = next_order
            name.save()
            # Process data:
            surname = sf.save(commit=False)
            surname.name = name
            # Manually set any data:
            surname.prefix = sf.cleaned_data["prefix"] if sf.cleaned_data["prefix"] != " prefix " else ""
            surname.primary = True # FIXME: why is this False?
            surname.save()
            # FIXME: last_saved, last_changed, last_changed_by
            dji.rebuild_cache(person)
            # FIXME: update probably_alive
            return redirect("/person/%s/name/%s" % (person.handle, name.order))
        else:
            action = "add"
    elif action == "save":
        # look up old data:
        person = Person.objects.get(handle=handle)
        oldname = person.name_set.get(order=order)
        oldsurname = oldname.surname_set.get(primary=True)
        # combine with user data:
        pf = PersonForm(request.POST, instance=person)
        pf.model = person
        nf = NameForm(request.POST, instance=oldname)
        nf.model = oldname
        sf = SurnameForm(request.POST, instance=oldsurname)
        if nf.is_valid() and sf.is_valid():
            # name.preferred and surname.primary get set False in the above is_valid()
            # person = pf.save()
            # Process data:
            oldname.person = person
            name = nf.save()
            # Manually set any data:
            name.suffix = nf.cleaned_data["suffix"] if nf.cleaned_data["suffix"] != " suffix " else ""
            name.preferred = True # FIXME: why is this False?
            update_last_changed(name, request.user.username)
            check_preferred(name, person)
            name.save()
            # Process data:
            oldsurname.name = name
            surname = sf.save(commit=False)
            # Manually set any data:
            surname.prefix = sf.cleaned_data["prefix"] if sf.cleaned_data["prefix"] != " prefix " else ""
            surname.primary = True # FIXME: why is this False?
            surname.save()
            # FIXME: last_saved, last_changed, last_changed_by
            dji.rebuild_cache(person)
            # FIXME: update probably_alive
            return redirect("/person/%s/name/%s" % (person.handle, name.order))
        else:
            action = "edit"
    context = RequestContext(request)
    context["action"] = action
    context["tview"] = _('Name')
    context["tviews"] = _('Names')
    context["view"] = 'name'
    context["handle"] = handle
    context["id"] = id
    context["person"] = person
    context["object"] = person
    context["nameform"] = nf
    context["surnameform"] = sf
    context["order"] = order
    context["next"] = "/person/%s/name/%d" % (person.handle, name.order)
    view_template = "view_name_detail.html"
    return render_to_response(view_template, context)
    
def process_person(request, context, handle, action): # view, edit, save
    """
    Process action on person. Can return a redirect.
    """
    context["tview"] = _("Person")
    context["tviews"] = _("People")
    if request.user.is_authenticated():
        if action in ["edit", "view"]:
            pf, nf, sf, person = get_person_forms(handle, empty=False)
        elif action == "add":
            pf, nf, sf, person = get_person_forms(handle=None, protect=False, empty=True)
        elif action == "delete":
            pf, nf, sf, person = get_person_forms(handle, protect=False, empty=True)
            person.delete()
            return redirect("/person/")
        elif action in ["save", "create"]: # could be create a new person
            # look up old data, if any:
            if handle:
                person = Person.objects.get(handle=handle)
                name = person.name_set.get(preferred=True)
                surname = name.surname_set.get(primary=True)
            else: # create new item
                person = Person(handle=create_id())
                name = Name(person=person, preferred=True)
                surname = Surname(name=name, primary=True, order=1)
                surname = Surname(name=name, 
                                  primary=True, 
                                  order=1,
                                  name_origin_type=NameOriginType.objects.get(val=NameOriginType._DEFAULT[0]))
            # combine with user data:
            pf = PersonForm(request.POST, instance=person)
            pf.model = person
            nf = NameFormFromPerson(request.POST, instance=name)
            nf.model = name
            sf = SurnameForm(request.POST, instance=surname)
            # check if valid:
            if nf.is_valid() and pf.is_valid() and sf.is_valid():
                # name.preferred and surname.primary get set False in the above is_valid()
                update_last_changed(person, request.user.username)
                person = pf.save()
                # Process data:
                name.person = person
                name = nf.save(commit=False)
                # Manually set any data:
                name.suffix = nf.cleaned_data["suffix"] if nf.cleaned_data["suffix"] != " suffix " else ""
                name.preferred = True # FIXME: why is this False?
                check_preferred(name, person)
                update_last_changed(name, request.user.username)
                name.save()
                # Process data:
                surname.name = name
                surname = sf.save(commit=False)
                # Manually set any data:
                surname.prefix = sf.cleaned_data["prefix"] if sf.cleaned_data["prefix"] != " prefix " else ""
                surname.primary = True # FIXME: why is this False?
                surname.save()
                # FIXME: last_saved, last_changed, last_changed_by
                dji.rebuild_cache(person)
                # FIXME: update probably_alive
                return redirect("/person/%s" % person.handle)
            else: 
                # need to edit again
                if handle:
                    action = "edit"
                else:
                    action = "add"
        else: # error?
            raise Http404(_("Requested %s does not exist.") % "person")
    else: # not authenticated
        # BEGIN NON-AUTHENTICATED ACCESS
        try:
            person = Person.objects.get(handle=handle)
        except:
            raise Http404(_("Requested %s does not exist.") % "person")
        if person.private:
            raise Http404(_("Requested %s does not exist.") % "person")
        pf, nf, sf, person = get_person_forms(handle, protect=True)
        # END NON-AUTHENTICATED ACCESS
    context["action"] = action
    context["view"] = "person"
    context["tview"] = _("Person")
    context["tviews"] = _("People")
    context["personform"] = pf
    context["nameform"] = nf
    context["surnameform"] = sf
    context["person"] = person
    context["object"] = person
    context["next"] = "/person/%s" % person.handle

def get_person_forms(handle, protect=False, empty=False, order=None):
    if handle:
        person = Person.objects.get(handle=handle)
    else:
        person = Person()
        #person.gramps_id = "I0000" # FIXME: get next ID
    ## get a name
    name = None
    if order is not None:
        try:
            name = person.name_set.get(order=order)
        except:
            pass
    if name is None:
        try:
            name = person.name_set.get(preferred=True)
        except:
            name = Name(person=person, preferred=True,
                        display_as=NameFormatType.objects.get(val=NameFormatType._DEFAULT[0]), 
                        sort_as=NameFormatType.objects.get(val=NameFormatType._DEFAULT[0]), 
                        name_type=NameType.objects.get(val=NameType._DEFAULT[0]))
    ## get a surname
    try:
        surname = name.surname_set.get(primary=True)
    except:
        surname = Surname(name=name, primary=True, 
                          name_origin_type=NameOriginType.objects.get(val=NameOriginType._DEFAULT[0]),
                          order=1)

    if protect and person.probably_alive:
        name.sanitize()
    pf = PersonForm(instance=person)
    pf.model = person
    name.suffix = make_empty(empty, name.suffix, " suffix ")
    nf = NameForm(instance=name)
    nf.model = name
    surname.prefix = make_empty(empty, surname.prefix, " prefix ")
    sf = SurnameForm(instance=surname)
    sf.model = surname
    return pf, nf, sf, person

def make_empty(empty, value, empty_value):
    if value:
        return value
    elif empty:
        return empty_value
    else:
        return value
