from django.shortcuts import render
from django.http import HttpResponse,Http404,JsonResponse,HttpResponseBadRequest
from django.views.generic import CreateView, DeleteView, ListView
import json
from .models import Picture
from .response import JSONResponse, response_mimetype
from .serialize import serialize
from django.views.decorators.http import require_POST,require_GET
from .noteshrink_module import AttrDict,notescan_main
from django.conf import settings
from django.http import HttpResponse
from .utils import random_string
import os
@require_GET
def download_pdf(request):
    filename=request.GET['filename']
    file_path = os.path.join(settings.PDF_ROOT, filename)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/pdf")
            response['Content-Disposition'] = 'attachment; filename=' + os.path.basename(file_path)
            return response
    else:
        raise Http404


def index(request):
    return render(request,'index.html')
#TODO: 1. Сделать чтобы сохранялись загруженные файлы по сессии
#DONE: 2. Удалять сразу не разрешенные файлы - не загружаются
#TODO: 3. Проверять отсутсвующие параметры в shrink
#TODO: 4. Проверять, существуют ли папки PNG_ROOT и PDF_ROOT - создавать если нет
#TODO: 5. Проверять максимальную длину названий файлов
#DONE: 6. Сделать кнопку для резета
@require_POST
def shrink(request):

    files = request.POST.getlist('files[]')
    existing_files = []
    for i in files:
        path = os.path.join(settings.MEDIA_ROOT,'pictures', i)
        if os.path.exists(path):
         existing_files.append(path)
    if len(existing_files)==0:
        return Http404
    on_off = lambda x: True if x=='on' else False
    try:
        num_colors = int(request.POST['num_colors'])
        sample_fraction = float(request.POST['sample_fraction'])*0.01
        sat_threshold = float(request.POST['sat_threshold'])
        value_threshold = float(request.POST['value_threshold'])
    except ValueError as e:
        return HttpResponseBadRequest(str(e))
    if request.POST['pdfname'].find('.pdf')==-1:

        pdfname=random_string(settings.RANDOM_STRING_LEN)+"_"+request.POST['pdfname']+'.pdf'
    else:
        pdfname=random_string(settings.RANDOM_STRING_LEN)+"_"+request.POST['pdfname']

    basename= random_string(settings.RANDOM_STRING_LEN)+"_"+request.POST['basename']
    options= {
    "basename": basename, #базовое название для картинки
    "filenames": existing_files, #массив путей к файлам
    "global_palette": on_off(request.POST['global_palette']), # одна палитра для всех картинок
    "num_colors": num_colors, #цветов на выходе
    "pdf_cmd": 'convert %i %o', # команда для пдф
    "pdfname": os.path.join(settings.PDF_ROOT,pdfname), #название выходного пдф файла
    "postprocess_cmd": None,
    "postprocess_ext": '_post.png', # название после процессинга (?)
    "quiet": False, # сократить выдачу
    "sample_fraction": sample_fraction, #пикселей брать за образец в %
    "sat_threshold": sat_threshold, #насыщенность фона
    "saturate": True, #насыщать
    "sort_numerically": on_off(request.POST['sort_numerically']), # оставить порядок следования
    "value_threshold": value_threshold, # пороговое значение фона
    "white_bg": on_off(request.POST['white_bg']), # белый фон
    "picture_folder": settings.PNG_ROOT #куда сохранять картинки
    }
    pngs,pdf = notescan_main(AttrDict(options))

    return JsonResponse({"pngs":pngs,"pdf":pdfname})


class PictureCreateView(CreateView):
    model = Picture
    fields = "__all__"
    template_name = 'index.html'
    def form_valid(self, form):
        self.object = form.save()
        files = [serialize(self.object)]
        data = {'files': files}
        response = JSONResponse(data, mimetype=response_mimetype(self.request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response

    def form_invalid(self, form):
        data = json.dumps(form.errors)
        return HttpResponse(content=data, status=400, content_type='application/json')



class PictureDeleteView(DeleteView):
    model = Picture

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        response = JSONResponse(True, mimetype=response_mimetype(request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response


class PictureListView(ListView):
    model = Picture

    def render_to_response(self, context, **response_kwargs):
        files = [ serialize(p) for p in self.get_queryset() ]
        data = {'files': files}
        response = JSONResponse(data, mimetype=response_mimetype(self.request))
        response['Content-Disposition'] = 'inline; filename=files.json'
        return response
