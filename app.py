from flask import Flask, request, send_file, render_template
from PIL import Image
import io
import os

app = Flask(__name__)

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'}
ALLOWED_OUTPUT_FORMATS = {'pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

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

    if not allowed_file(file.filename):
        return "Formato de arquivo não suportado.", 400

    if output_format not in ALLOWED_OUTPUT_FORMATS:
        return "Formato de saída não suportado.", 400

    try:
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

    except Exception as e:
        return f"Erro na conversão: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
