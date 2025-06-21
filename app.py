from flask import Flask, request, send_file, render_template
from PIL import Image
from pydub import AudioSegment
import io
import os

app = Flask(__name__)

# Extensões permitidas por categoria
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'ogg'}
ALLOWED_OUTPUT_FORMATS = ALLOWED_IMAGE_EXTENSIONS.union({'pdf'}).union(ALLOWED_AUDIO_EXTENSIONS)

def allowed_file(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    return ext in ALLOWED_OUTPUT_FORMATS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return "Nenhum arquivo enviado", 400

    file = request.files['file']
    output_format = request.form.get('output-format', '').lower()

    if file.filename == '':
        return "Nenhum arquivo selecionado", 400

    input_ext = file.filename.rsplit('.', 1)[1].lower()
    if not allowed_file(file.filename):
        return "Formato de arquivo não suportado.", 400

    if output_format not in ALLOWED_OUTPUT_FORMATS:
        return "Formato de saída não suportado.", 400

    try:
        if input_ext in ALLOWED_IMAGE_EXTENSIONS:
            # Converte imagem (incluindo para PDF)
            img = Image.open(file.stream)
            buf = io.BytesIO()
            if output_format == 'pdf':
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                img.save(buf, format='PDF')
                mimetype = 'application/pdf'
            else:
                img = img.convert('RGB')
                img.save(buf, format=output_format.upper())
                mimetype = f'image/{output_format}'
            buf.seek(0)
            output_filename = os.path.splitext(file.filename)[0] + '.' + output_format
            return send_file(buf, as_attachment=True, download_name=output_filename, mimetype=mimetype)

        elif input_ext in ALLOWED_AUDIO_EXTENSIONS:
            # Converte áudio usando pydub
            audio = AudioSegment.from_file(file.stream, format=input_ext)
            buf = io.BytesIO()
            audio.export(buf, format=output_format)
            buf.seek(0)
            mimetype = f'audio/{output_format}'
            output_filename = os.path.splitext(file.filename)[0] + '.' + output_format
            return send_file(buf, as_attachment=True, download_name=output_filename, mimetype=mimetype)

        else:
            return "Conversão para esse tipo ainda não suportada.", 400

    except Exception as e:
        return f"Erro na conversão: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
