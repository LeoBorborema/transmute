import os
import subprocess
from flask import Flask, request, render_template, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from PIL import Image
from docx import Document
from fpdf import FPDF
import tempfile

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'  # necessário para flash messages
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = set([
    # todos os formatos do HTML para entrada
    'pdf', 'docx', 'doc', 'txt', 'rtf', 'odt', 'html', 'md',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg',
    'mp3', 'wav', 'aac', 'flac', 'ogg', 'm4a', 'wma',
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'mpeg', '3gp'
])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_audio(input_path, output_path, output_format):
    sound = AudioSegment.from_file(input_path)
    sound.export(output_path, format=output_format)

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

def convert_video(input_path, output_path, output_format):
    cmd = ['ffmpeg', '-i', input_path, '-y', output_path]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def convert_doc_to_pdf(input_path, output_path):
    # Usa python-docx para abrir .docx e fpdf para gerar pdf simples
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

        output_filename = f"converted.{output_format}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        try:
            # Detecta tipo para decidir conversão
            if input_format in ['mp3','wav','aac','flac','ogg','m4a','wma'] and \
               output_format in ['mp3','wav','aac','flac','ogg','m4a','wma']:
                convert_audio(input_path, output_path, output_format)

            elif input_format in ['jpg','jpeg','png','gif','bmp','tiff','webp','svg'] and \
                 output_format in ['jpg','jpeg','png','gif','bmp','tiff','webp','pdf']:
                # Para SVG ou pdf, aqui trataremos PDF apenas para bitmap via imagem
                if input_format == 'svg':
                    # Converter SVG para PNG via cairosvg se disponível (opcional)
                    from cairosvg import svg2png
                    png_path = output_path.rsplit('.',1)[0] + ".png"
                    svg2png(url=input_path, write_to=png_path)
                    convert_image(png_path, output_path, output_format)
                    os.remove(png_path)
                elif output_format == 'pdf':
                    # Converter imagem para PDF
                    im = Image.open(input_path)
                    im.save(output_path, "PDF", resolution=100.0)
                else:
                    convert_image(input_path, output_path, output_format)

            elif input_format in ['mp4','avi','mov','wmv','flv','mkv','webm','mpeg','3gp'] and \
                 output_format in ['mp4','avi','mov','wmv','flv','mkv','webm','mpeg','3gp','mp3','wav','aac','flac','ogg','m4a','wma']:
                # Se saída for áudio, extrai áudio com ffmpeg
                if output_format in ['mp3','wav','aac','flac','ogg','m4a','wma']:
                    audio_path = output_path.rsplit('.',1)[0] + ".mp3"
                    cmd = ['ffmpeg', '-i', input_path, '-q:a', '0', '-map', 'a', audio_path, '-y']
                    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    output_path = audio_path
                else:
                    convert_video(input_path, output_path, output_format)

            elif input_format in ['docx'] and output_format == 'pdf':
                convert_doc_to_pdf(input_path, output_path)

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
            # Limpeza
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
    else:
        flash('Arquivo não permitido ou formato não suportado.')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
