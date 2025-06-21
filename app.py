import os
import tempfile
import subprocess
from flask import Flask, request, render_template, send_file, abort
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024  # 30 MB

ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'mp3', 'wav', 'mp4', 'mov', 'avi',
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'
}

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    return ext in ALLOWED_EXTENSIONS

def resize_image_if_needed(input_path, max_width=1920, max_height=1080):
    with Image.open(input_path) as img:
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height))
            img.save(input_path)

def convert_file(input_path, output_path, input_ext, output_ext):
    # Aqui só exemplo básico, ajuste para suas conversões completas
    
    if input_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'] and output_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff']:
        # Imagem para imagem: redimensionar para evitar peso
        resize_image_if_needed(input_path)
        img = Image.open(input_path)
        img.save(output_path)
        return

    if input_ext in ['mp4', 'mov', 'avi'] and output_ext in ['mp4', 'mov', 'avi']:
        # Vídeo para vídeo com limite 720p
        command = [
            'ffmpeg', '-i', input_path,
            '-vf', 'scale=-2:720',
            '-preset', 'fast', '-crf', '28',
            output_path
        ]
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return

    if input_ext in ['mp4', 'mov', 'avi'] and output_ext == 'mp3':
        # Vídeo para áudio mp3
        command = [
            'ffmpeg', '-i', input_path,
            '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
            output_path
        ]
        subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return

    # Você pode adicionar outras conversões específicas aqui

    # Caso não tenha conversão específica, copie arquivo
    from shutil import copyfile
    copyfile(input_path, output_path)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        abort(400, "Arquivo não enviado")
    file = request.files['file']
    if file.filename == '':
        abort(400, "Arquivo inválido")
    if not allowed_file(file.filename):
        abort(400, "Formato não suportado")

    input_ext = file.filename.rsplit('.', 1)[-1].lower()
    output_ext = request.form.get('output-format')
    if not output_ext:
        abort(400, "Formato de saída não selecionado")

    input_filename = secure_filename(file.filename)
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, input_filename)
        file.save(input_path)

        output_filename = f"converted.{output_ext}"
        output_path = os.path.join(tmpdir, output_filename)

        convert_file(input_path, output_path, input_ext, output_ext)

        try:
            return send_file(output_path, as_attachment=True, download_name=output_filename)
        finally:
            # arquivos temporários são apagados automaticamente por TemporaryDirectory
            pass


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
