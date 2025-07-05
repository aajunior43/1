import gradio as gr
import fitz  # PyMuPDF
import zipfile
import os
import shutil
from pathlib import Path
import time
from PIL import Image

def converter_pdfs(pdfs, dpi, output_format, image_quality, progress=gr.Progress(track_tqdm=True)):
    logs = []
    resultados = []
    previews = []
    out_dir = 'saida_gradio'
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    if not pdfs:
        return [], [], "❌ Nenhum arquivo PDF selecionado!", ""

    total = len(pdfs)
    start_time = time.time()
    for idx, pdf_path in enumerate(pdfs):
        nome = Path(pdf_path).stem
        try:
            doc = fitz.open(pdf_path)
        except fitz.EmptyFileError:
            logs.append(f'{nome}: Erro - O arquivo PDF está vazio ou corrompido.')
            continue
        except fitz.FileDataError:
            logs.append(f'{nome}: Erro - Não foi possível abrir o arquivo PDF. Pode estar corrompido ou protegido por senha.')
            continue
        except Exception as e:
            logs.append(f'{nome}: Erro inesperado ao abrir o PDF - {e}')
            continue
            pdf_dir = os.path.join(out_dir, nome)
            os.makedirs(pdf_dir, exist_ok=True)
            num_pages = len(doc)
            for i, page in enumerate(doc):
                mat = fitz.Matrix(dpi / 72, dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                # Determine image extension based on format
                img_ext = output_format.lower()
                if img_ext == 'jpg':
                    img_ext = 'jpeg' # Pillow uses 'jpeg' for JPG
                img_path = os.path.join(pdf_dir, f'pagina_{i+1:03d}.{img_ext}')

                if output_format.upper() in ['JPG', 'WEBP']:
                    pix.save(img_path, output_format.lower(), quality=image_quality)
                else: # PNG
                    pix.save(img_path)

                logs.append(f'{nome}: Página {i+1} convertida para {output_format.upper()}.')
                if i == 0:
                    # Salvar preview da primeira página
                    preview_path = os.path.join(pdf_dir, f'preview.{img_ext}')
                    if output_format.upper() in ['JPG', 'WEBP']:
                        pix.save(preview_path, output_format.lower(), quality=image_quality)
                    else: # PNG
                        pix.save(preview_path)
                    previews.append(preview_path)
                progress((idx + i / num_pages) / total, desc=f'Convertendo {nome} ({i+1}/{num_pages})')
            doc.close()
            # Compactar se multipágina
            imgs = [os.path.join(pdf_dir, f) for f in os.listdir(pdf_dir) if f.endswith(f'.{img_ext}')]
            if len(imgs) > 1:
                zip_path = os.path.join(out_dir, f'{nome}.zip')
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for img in imgs:
                        zipf.write(img, arcname=os.path.basename(img))
                resultados.append(zip_path)
                logs.append(f'{nome}: Compactado em ZIP.')
            else:
                resultados.append(imgs[0])
            logs.append(f'{nome}: {num_pages} página(s) convertida(s)!')
        except Exception as e:
            logs.append(f'{nome}: Erro - {e}')
    tempo = time.time() - start_time
    msg = f'✅ Conversão concluída! {len(resultados)} arquivo(s) gerado(s) em {tempo:.1f} segundos.'
    return resultados, previews, msg, '\n'.join(logs)

theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="cyan",
    neutral_hue="slate",
    font=["Segoe UI", "Roboto", "sans-serif"],
    text_size="lg"
)

with gr.Blocks(theme=theme, title="Conversor Moderno de PDF para PNG", css="""
    body { font-family: 'Segoe UI', 'Roboto', 'sans-serif'; }
    .gradio-container { background: linear-gradient(to right, #2c3e50, #34495e); color: #ecf0f1; }
    .gr-button-primary { background-color: #3498db; border-color: #3498db; color: white; font-weight: bold; }
    .gr-button-primary:hover { background-color: #2980b9; border-color: #2980b9; }
    .gr-button-secondary { background-color: #7f8c8d; border-color: #7f8c8d; color: white; }
    .gr-button-secondary:hover { background-color: #6c7a7d; border-color: #6c7a7d; }
    .gr-box, .gr-panel, .gr-group { background-color: #3b506b; border: 1px solid #4a6280; border-radius: 10px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); }
    .gr-gallery { background-color: #2e4053; border-radius: 8px; }
    .gr-textbox { background-color: #2e4053; color: #ecf0f1; border: 1px solid #4a6280; border-radius: 5px; }
    .gr-label { color: #ADD8E6; font-weight: bold; }
    .gr-text-input { color: #ecf0f1; }
    .gr-slider { color: #ADD8E6; }
    .gr-slider-fill { background-color: #3498db; }
    .gr-file-input { background-color: #2e4053; border: 1px dashed #3498db; border-radius: 8px; padding: 20px; text-align: center; }
    .gr-file-input p { color: #ADD8E6; }
    .gr-file-input:hover { border-color: #2980b9; }
    .gr-interface-panel { padding: 20px; }
    .gr-interface-panel h2 { margin-top: 0; }
    """) as demo:
    gr.Markdown("""
    <h1 style="text-align: center; color: #ADD8E6;">✨ Conversor Moderno de PDF para PNG ✨</h1>
    <p style="text-align: center; font-size: 1.1em; color: #E0FFFF;">
    Selecione um ou mais arquivos PDF, ajuste a resolução (DPI) e clique em "Converter" para iniciar o processo.
    </p>
    <p style="text-align: center; font-size: 0.9em; color: #B0C4DE;">
    Desenvolvido por <b>Aleksandro Alves</b> | Suporte a múltiplos PDFs, pré-visualização e logs detalhados.
    </p>
    """)

    with gr.Row():
        with gr.Column(scale=1):
            pdf_input = gr.File(label='📁 Arraste e Solte ou Clique para Selecionar PDFs', file_count='multiple', type='filepath', interactive=True)
            dpi_slider = gr.Slider(minimum=72, maximum=600, value=300, step=12, label='⚙️ Resolução (DPI): Qualidade da Imagem', info="Um DPI maior resulta em imagens de melhor qualidade, mas aumenta o tempo de conversão e o tamanho do arquivo.")
            output_format_radio = gr.Radio(
                choices=["PNG", "JPG", "WEBP"],
                value="PNG",
                label="🖼️ Formato de Saída",
                info="Escolha o formato de imagem para a conversão."
            )
            image_quality_slider = gr.Slider(
                minimum=1,
                maximum=100,
                value=90,
                step=1,
                label="✨ Qualidade da Imagem (para JPG/WEBP)",
                info="Ajuste a qualidade da imagem (1-100). Maior qualidade = maior arquivo.",
                visible=False # Initially hidden
            )
            convert_button = gr.Button("🚀 Converter PDFs", variant="primary")
            clear_button = gr.Button("🧹 Limpar Tudo", variant="secondary")

        with gr.Column(scale=2):
            message_output = gr.Textbox(label='Mensagem', lines=1, interactive=False)
            converted_files_output = gr.Files(label='Imagens/ZIPs convertidos')
            preview_gallery_output = gr.Gallery(label='Prévia da Primeira Página', show_label=True, columns=4, height='auto')
            log_output = gr.Textbox(label='Log de Conversão', lines=8, interactive=False)

    output_format_radio.change(
        fn=lambda value: gr.Slider(visible=value in ["JPG", "WEBP"]),
        inputs=output_format_radio,
        outputs=image_quality_slider
    )

    convert_button.click(
        fn=converter_pdfs,
        inputs=[pdf_input, dpi_slider, output_format_radio, image_quality_slider],
        outputs=[converted_files_output, preview_gallery_output, message_output, log_output]
    )

    clear_button.click(
        fn=lambda: [None, None, "", "", 300, "PNG", 90, None],
        outputs=[converted_files_output, preview_gallery_output, message_output, log_output, dpi_slider, output_format_radio, image_quality_slider, pdf_input]
    )

def main():
    demo.launch(share=False, inbrowser=True)

if __name__ == '__main__':
    main() 