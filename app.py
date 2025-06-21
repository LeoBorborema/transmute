from flask import Flask, render_template, request, send_file
import os
import tempfile
import subprocess
from werkzeug.utils import secure_filename
from PIL import Image
from docx import Document
from fpdf import FPDF

app = Flask(__name__)
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_file():
    file = request.files.get('file')
    output_format = request.form.get('output-format')

    if not file or not output_format:
        return "Arquivo e formato de saída são obrigatórios.", 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(input_path)

    input_ext = os.path.splitext(filename)[1].lower().replace('.', '')
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], f"converted.{output_format}")

    try:
        if input_ext in ['mp4', 'avi', 'mov', 'mkv'] and output_format in ['mp4', 'avi', 'mov', 'mp3']:
            # Conversão de vídeo ou vídeo para áudio via FFmpeg
            cmd = ['ffmpeg', '-i', input_path, output_path, '-y']
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        elif input_ext in ['png', 'jpg', 'jpeg'] and output_format == 'pdf':
            image = Image.open(input_path).convert('RGB')
            image.save(output_path)

        elif input_ext == 'docx' and output_format == 'pdf':
            # Simulação básica (FPDF + texto plano)
            doc = Document(input_path)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            for para in doc.paragraphs:
                pdf.multi_cell(0, 10, para.text)
            pdf.output(output_path)

        else:
            return "Formato de conversão não suportado neste momento.", 400

        return send_file(output_path, as_attachment=True)
    except Exception as e:
        return f"Erro ao converter: {str(e)}", 500
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)
        if os.path.exists(output_path):
            os.remove(output_path)

if __name__ == '__main__':
    app.run(debug=True)
