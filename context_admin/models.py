from django.contrib import admin
from django import forms, template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe
from django.shortcuts import get_object_or_404, render_to_response
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.contrib.admin.options import IncorrectLookupParameters
from django.db.models.fields.related import ForeignKey
from django.contrib.admin import widgets, helpers
from django.utils.translation import ugettext as _
from django.utils.translation import ungettext
from django.utils.encoding import force_unicode
from django.db import models

csrf_protect_m = method_decorator(csrf_protect)

class ContextModelAdmin(admin.ModelAdmin):

    models = None
    excluded = None

    def __init__(self, model, admin_site):

        super(ContextModelAdmin,self).__init__(model, admin_site)
        self.inners = []
        
        if not self.models:
            self.models = []
            for model in models.get_models():
                for field in model._meta.fields:
                    if isinstance(field, ForeignKey):
                        if field.rel.to == self.model:
                            self.models.append(model)


        if not self.excluded:
            self.excluded = []

        for inner in self.models:
            if inner not in self.excluded:
                self.inners.append(inner(self,inner.model,admin_site))
        


    def get_urls(self):
        #import pdb; pdb.set_trace()
        urls = super(ContextModelAdmin, self).get_urls()
        my_urls = []

        for inner in self.inners:
            my_urls.extend(inner.get_urls())
        return my_urls + urls

    
    def change_view(self, request, object_id, extra_context=None):
        my_context = {
            'context_model_admin': self,
        }
        return super(ContextModelAdmin, self).change_view(request, object_id, extra_context=my_context)

    # TODO: Use the super class method insted of overwrite the whole method
    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        opts = self.model._meta
        app_label = opts.app_label
        ordered_objects = opts.get_ordered_objects()
        context.update({
            'add': add,
            'change': change,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, obj),
            'has_delete_permission': self.has_delete_permission(request, obj),
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'ordered_objects': ordered_objects,
            'form_url': mark_safe(form_url),
            'opts': opts,
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
            'root_path': self.admin_site.root_path,
        })
        if add and self.add_form_template is not None:
            form_template = self.add_form_template
        else:
            form_template = self.change_form_template
        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(form_template or [
            "context_admin/%s/%s/change_form.html" % (app_label, opts.object_name.lower()),
            "context_admin/%s/change_form.html" % app_label,
            "context_admin/change_form.html"
        ], context, context_instance=context_instance)


class InnerContextModelAdmin(admin.ModelAdmin):

    def __init__(self, context_model_admin, model, admin_site):
        self.context_model_admin = context_model_admin
        super(InnerContextModelAdmin, self).__init__(model, admin_site)

    def render_achange_form(self, request, context, add=False, change=False, form_url='', obj=None):
        pass

    
    def queryset(self, request):
        # Here I need to find out who is the the parent
        qs = super(InnerContextModelAdmin,self).queryset(request)
        #import pdb; pdb.set_trace()
        for field in self.model._meta.fields:
            if isinstance(field, ForeignKey):
                if field.rel.to == self.context_model_admin.model:
                    qs = qs.filter(**{field.name:self.parent_id})


        return qs

    def set_parrent_context_admin(self, request, parent_id):
        self.parent_id = parent_id


    @csrf_protect_m
    def changelist_view(self, request, parent_id, extra_context=None):
        "The 'change list' admin view for this model."
        
        self.set_parrent_context_admin(request, parent_id)

        from django.contrib.admin.views.main import ERROR_FLAG
        opts = self.model._meta
        app_label = opts.app_label
        if not self.has_change_permission(request, None):
            raise PermissionDenied

        # Check actions to see if any are available on this changelist
        actions = self.get_actions(request)

        # Remove action checkboxes if there aren't any actions available.
        list_display = list(self.list_display)
        if not actions:
            try:
                list_display.remove('action_checkbox')
            except ValueError:
                pass

        ChangeList = self.get_changelist(request)
        try:
            cl = ChangeList(request, self.model, list_display, self.list_display_links,
                self.list_filter, self.date_hierarchy, self.search_fields,
                self.list_select_related, self.list_per_page, self.list_editable, self)
        except IncorrectLookupParameters:
            # Wacky lookup parameters were given, so redirect to the main
            # changelist page, without parameters, and pass an 'invalid=1'
            # parameter via the query string. If wacky parameters were given
            # and the 'invalid=1' parameter was already in the query string,
            # something is screwed up with the database, so display an error
            # page.
            if ERROR_FLAG in request.GET.keys():
                return render_to_response('admin/invalid_setup.html', {'title': _('Database error')})
            return HttpResponseRedirect(request.path + '?' + ERROR_FLAG + '=1')

        # If the request was POSTed, this might be a bulk action or a bulk
        # edit. Try to look up an action or confirmation first, but if this
        # isn't an action the POST will fall through to the bulk edit check,
        # below.
        action_failed = False
        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)

        # Actions with no confirmation
        if (actions and request.method == 'POST' and
                'index' in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, queryset=cl.get_query_set())
                if response:
                    return response
                else:
                    action_failed = True
            else:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                self.message_user(request, msg)
                action_failed = True

        # Actions with confirmation
        if (actions and request.method == 'POST' and
                helpers.ACTION_CHECKBOX_NAME in request.POST and
                'index' not in request.POST and '_save' not in request.POST):
            if selected:
                response = self.response_action(request, queryset=cl.get_query_set())
                if response:
                    return response
                else:
                    action_failed = True

        # If we're allowing changelist editing, we need to construct a formset
        # for the changelist given all the fields to be edited. Then we'll
        # use the formset to validate/process POSTed data.
        formset = cl.formset = None

        # Handle POSTed bulk-edit data.
        if (request.method == "POST" and cl.list_editable and
                '_save' in request.POST and not action_failed):
            FormSet = self.get_changelist_formset(request)
            formset = cl.formset = FormSet(request.POST, request.FILES, queryset=cl.result_list)
            if formset.is_valid():
                changecount = 0
                for form in formset.forms:
                    if form.has_changed():
                        obj = self.save_form(request, form, change=True)
                        self.save_model(request, obj, form, change=True)
                        form.save_m2m()
                        change_msg = self.construct_change_message(request, form, None)
                        self.log_change(request, obj, change_msg)
                        changecount += 1

                if changecount:
                    if changecount == 1:
                        name = force_unicode(opts.verbose_name)
                    else:
                        name = force_unicode(opts.verbose_name_plural)
                    msg = ungettext("%(count)s %(name)s was changed successfully.",
                                    "%(count)s %(name)s were changed successfully.",
                                    changecount) % {'count': changecount,
                                                    'name': name,
                                                    'obj': force_unicode(obj)}
                    self.message_user(request, msg)

                return HttpResponseRedirect(request.get_full_path())

        # Handle GET -- construct a formset for display.
        elif cl.list_editable:
            FormSet = self.get_changelist_formset(request)
            formset = cl.formset = FormSet(queryset=cl.result_list)

        # Build the list of media to be used by the formset.
        if formset:
            media = self.media + formset.media
        else:
            media = self.media

        # Build the action form and populate it with available actions.
        if actions:
            action_form = self.action_form(auto_id=None)
            action_form.fields['action'].choices = self.get_action_choices(request)
        else:
            action_form = None

        selection_note_all = ungettext('%(total_count)s selected',
            'All %(total_count)s selected', cl.result_count)

        context = {
            'module_name': force_unicode(opts.verbose_name_plural),
            'selection_note': _('0 of %(cnt)s selected') % {'cnt': len(cl.result_list)},
            'selection_note_all': selection_note_all % {'total_count': cl.result_count},
            'title': cl.title,
            'is_popup': cl.is_popup,
            'cl': cl,
            'media': media,
            'has_add_permission': self.has_add_permission(request),
            'root_path': self.admin_site.root_path,
            'app_label': app_label,
            'action_form': action_form,
            'actions_on_top': self.actions_on_top,
            'actions_on_bottom': self.actions_on_bottom,
            'actions_selection_counter': self.actions_selection_counter,
        }
        context.update(extra_context or {})

        context['context_inner_model_admin'] = self

        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(self.change_list_template or [
            'context_admin/%s/%s/inner_change_list.html' % (app_label, opts.object_name.lower()),
            'context_admin/%s/inner_change_list.html' % app_label,
            'context_admin/inner_change_list.html'
        ], context, context_instance=context_instance)

    

    def add_view(self, request, parent_id, form_url='', extra_context=None):
        self.set_parrent_context_admin(request, parent_id)
        return super(InnerContextModelAdmin, self).add_view(request, form_url, extra_context)

    
    def change_view(self, request, parent_id, object_id, extra_context=None):
        #import pdb; pdb.set_trace()
        self.set_parrent_context_admin(request, parent_id)
        return super(InnerContextModelAdmin, self).change_view(request, object_id, extra_context)



    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        opts = self.model._meta
        app_label = opts.app_label
        ordered_objects = opts.get_ordered_objects()
        context.update({
            'add': add,
            'change': change,
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request, obj),
            'has_delete_permission': self.has_delete_permission(request, obj),
            'has_file_field': True, # FIXME - this should check if form or formsets have a FileField,
            'has_absolute_url': hasattr(self.model, 'get_absolute_url'),
            'ordered_objects': ordered_objects,
            'form_url': mark_safe(form_url),
            'opts': opts,
            'content_type_id': ContentType.objects.get_for_model(self.model).id,
            'save_as': self.save_as,
            'save_on_top': self.save_on_top,
            'root_path': self.admin_site.root_path,
        })
        if add and self.add_form_template is not None:
            form_template = self.add_form_template
        else:
            form_template = self.change_form_template
        context_instance = template.RequestContext(request, current_app=self.admin_site.name)
        return render_to_response(form_template or [
            "context_admin/%s/%s/change_form.html" % (app_label, opts.object_name.lower()),
            "context_admin/%s/change_form.html" % app_label,
            "context_admin/change_form.html"
        ], context, context_instance=context_instance)


    def get_urls(self):
        from django.conf.urls.defaults import *
        #from django.core.urlresolvers import reverse
        urls = super(InnerContextModelAdmin, self).get_urls()

        info = self.model._meta.app_label, self.model._meta.module_name

        #change_list_url = reverse('%s_%s_changelist' % info)

        my_urls = patterns('',
            url(r'^(?P<parent_id>\d+)/%s/%s/$' % (info), self.changelist_view, name="inner_changelist_view"),
            url(r'^(?P<parent_id>\d+)/%s/%s/add/$' % (info), self.add_view, name="inner_add_view"),
            url(r'^(?P<parent_id>\d+)/%s/%s/(?P<object_id>.+)/$' % (info), self.change_view, name="inner_change_view"),
        )
        return my_urls