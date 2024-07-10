import os
import re
import openai
from datetime import datetime
from apify import Actor
from youtube_transcript_api import YouTubeTranscriptApi as yta

async def extrair_transcricao_youtube(vid_id, language='pt'):
    try:
        data = yta.get_transcript(vid_id, languages=[language])
        transcript_plana = '\n'.join([value['text'] for value in data])
        return transcript_plana
    except Exception as e:
        Actor.log.error(f"Erro ao extrair transcrição: {e}")
        return None

def extrair_metadados(transcricao):
    titulo = transcricao.split('\n')[0]
    data = datetime.now().strftime('%d/%m/%Y')
    topicos = re.findall(r'\b([A-Za-zÀ-ÿ0-9\s]+)\b', transcricao)
    topicos = list(dict.fromkeys(topicos))
    topicos = topicos[:10]
    return titulo, data, topicos

async def gerar_faq(transcricao):
    prompt = f"Baseado no conteúdo da seguinte transcrição em português, gere 30 perguntas e respostas:\n\n{transcricao}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            n=1,
            temperature=0.5,
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        Actor.log.error(f"Erro ao gerar FAQ: {e}")
        return None

async def gerar_resumo(transcricao):
    prompt = f"Resuma a seguinte transcrição em português, destacando os pontos principais e as informações mais importantes:\n\n{transcricao}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            n=1,
            temperature=0.5,
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        Actor.log.error(f"Erro ao gerar resumo: {e}")
        return None

async def salvar_arquivo(conteudo, file_path):
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(conteudo)
    except Exception as e:
        Actor.log.error(f"Erro ao salvar arquivo: {e}")

async def main() -> None:
    async with Actor:
        Actor.log.info('Hello from the Actor!')

        # Configurar a chave da API OpenAI
        openai.api_key = os.getenv('OPENAI_API_KEY')

        # Obter a URL do vídeo do YouTube a partir das variáveis de entrada do Apify
        video_url = Actor.input.get('VIDEO_URL')
        if not video_url:
            Actor.log.error("URL do vídeo não fornecida.")
            return

        # Extrair o ID do vídeo da URL
        vid_id = re.search(r"v=([^&]+)", video_url)
        if vid_id:
            vid_id = vid_id.group(1)
        else:
            Actor.log.error("URL inválida.")
            return

        # Extrair transcrição do YouTube
        transcricao_plana = await extrair_transcricao_youtube(vid_id, language='pt')

        if transcricao_plana:
            # Salvar transcrição em texto plano
            await salvar_arquivo(transcricao_plana, "transcricao_plana_pt.txt")

            # Extrair metadados
            titulo, data, topicos = extrair_metadados(transcricao_plana)

            # Criar string dos metadados
            metadados = f"Título da aula: {titulo}\nData da aula: {data}\nTópicos principais cobertos na aula:\n"
            for i, topico in enumerate(topicos, start=1):
                metadados += f"{i}. {topico}\n"

            # Salvar metadados em um arquivo
            await salvar_arquivo(metadados, 'metadados.txt')

            # Gerar FAQ
            faq = await gerar_faq(transcricao_plana)
            if faq:
                await salvar_arquivo(faq, 'faq.txt')

            # Gerar resumo
            resumo = await gerar_resumo(transcricao_plana)
            if resumo:
                await salvar_arquivo(resumo, 'resumo.txt')

            Actor.log.info("Transcrição, FAQ, metadados e resumo gerados e salvos.")
        else:
            Actor.log.error("Não foi possível processar a transcrição.")
