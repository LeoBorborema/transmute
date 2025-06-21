import os
import subprocess
import tempfile
from flask import Flask, request, render_template, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from PIL import Image
from docx import Document
from fpdf import FPDF
from pdf2image import convert_from_path

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = set([
    'pdf', 'docx', 'doc', 'txt', 'rtf', 'odt', 'html', 'md',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg',
    'mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a', 'wma',
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'mpeg', '3gp'
])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_audio(input_path, output_path):
    cmd = ['ffmpeg', '-i', input_path, '-y', output_path]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def convert_image(input_path, output_path, output_format):
    im = Image.open(input_path)
    if output_format == 'jpg':
        output_format = 'JPEG'
    elif output_format == 'tiff':
        output_format = 'TIFF'
    elif output_format == 'png':
        output_format = 'PNG'
    elif output_format == 'gif':
        output_format = 'GIF'
    elif output_format == 'bmp':
        output_format = 'BMP'
    elif output_format == 'webp':
        output_format = 'WEBP'
    else:
        output_format = output_format.upper()
    im.convert('RGB').save(output_path, output_format)

def convert_video(input_path, output_path):
    cmd = ['ffmpeg', '-i', input_path, '-y', output_path]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def convert_doc_to_pdf(input_path, output_path):
    doc = Document(input_path)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for para in doc.paragraphs:
        text = para.text
        pdf.multi_cell(0, 10, text)
    pdf.output(output_path)

def convert_txt_to_pdf(input_path, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            pdf.multi_cell(0, 10, line.strip())
    pdf.output(output_path)

def convert_pdf_to_images(input_path, output_dir, output_format):
    pages = convert_from_path(input_path)
    image_paths = []
    for i, page in enumerate(pages):
        img_path = os.path.join(output_dir, f'page_{i+1}.{output_format}')
        page.save(img_path, output_format.upper())
        image_paths.append(img_path)
    return image_paths

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        flash('Nenhum arquivo enviado')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('Nenhum arquivo selecionado')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        input_format = file.filename.rsplit('.', 1)[1].lower()
        output_format = request.form.get('output-format').lower()
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        try:
            output_filename = f"converted.{output_format}"
            output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

            # Áudio para áudio
            audio_formats = ['mp3','wav','aac','flac','ogg','m4a','wma']
            if input_format in audio_formats and output_format in audio_formats:
                convert_audio(input_path, output_path)

            # Imagem para imagem/pdf
            elif input_format in ['jpg','jpeg','png','gif','bmp','tiff','webp'] and output_format in ['jpg','jpeg','png','gif','bmp','tiff','webp','pdf']:
                if output_format == 'pdf':
                    im = Image.open(input_path)
                    im.save(output_path, "PDF", resolution=100.0)
                else:
                    convert_image(input_path, output_path, output_format)

            # Vídeo para vídeo ou áudio
            video_formats = ['mp4','avi','mov','wmv','flv','mkv','webm','mpeg','3gp']
            if input_format in video_formats:
                if output_format in video_formats:
                    convert_video(input_path, output_path)
                elif output_format in audio_formats:
                    audio_path = output_path.rsplit('.',1)[0] + ".mp3"
                    cmd = ['ffmpeg', '-i', input_path, '-q:a', '0', '-map', 'a', audio_path, '-y']
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    output_path = audio_path
                else:
                    flash('Formato de saída não suportado para vídeo.')
                    return redirect(url_for('index'))

            # DOCX para PDF ou imagem
            elif input_format == 'docx':
                if output_format == 'pdf':
                    convert_doc_to_pdf(input_path, output_path)
                elif output_format in ['jpg','jpeg','png','gif','bmp','tiff','webp']:
                    tmp_pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_doc.pdf')
                    convert_doc_to_pdf(input_path, tmp_pdf_path)
                    images = convert_pdf_to_images(tmp_pdf_path, app.config['UPLOAD_FOLDER'], output_format)
                    if images:
                        os.rename(images[0], output_path)
                        for img in images[1:]:
                            os.remove(img)
                    os.remove(tmp_pdf_path)
                else:
                    flash('Conversão de DOCX para esse formato não suportada.')
                    return redirect(url_for('index'))

            # PDF para imagem ou PDF (reenvio)
            elif input_format == 'pdf':
                if output_format == 'pdf':
                    output_path = input_path  # sem conversão, apenas envio
                elif output_format in ['jpg','jpeg','png','gif','bmp','tiff','webp']:
                    images = convert_pdf_to_images(input_path, app.config['UPLOAD_FOLDER'], output_format)
                    if images:
                        # Para simplificar, envia a primeira página convertida
                        output_path = images[0]
                        # Remove as demais páginas convertidas
                        for img_path in images[1:]:
                            os.remove(img_path)
                    else:
                        flash('Falha ao converter PDF em imagem.')
                        return redirect(url_for('index'))
                else:
                    flash('Conversão de PDF para esse formato não suportada.')
                    return redirect(url_for('index'))

            # TXT para PDF
            elif input_format == 'txt' and output_format == 'pdf':
                convert_txt_to_pdf(input_path, output_path)

            else:
                flash('Conversão para esse formato não está implementada.')
                return redirect(url_for('index'))

            return send_file(output_path, as_attachment=True, download_name=f'arquivo_convertido.{output_format}')

        except Exception as e:
            flash(f'Erro durante conversão: {str(e)}')
            return redirect(url_for('index'))

        finally:
            if os.path.exists(input_path) and input_path != output_path:
                os.remove(input_path)
            # Não removo output_path porque será enviado para o usuário

    else:
        flash('Arquivo não permitido ou formato não suportado.')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
