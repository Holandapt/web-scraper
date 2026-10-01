import requests
import time
import csv
import random
import concurrent.futures
import threading
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozzila/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "en-US, en;q=0.9"
}

MAX_THREADS = 10
#Trava a escrita para evitar conflitos no arquivo CSV
csv_lock = threading.Lock()

#Essa função prepara o arquivo onde os dados serão salvos:
def setup_csv():
    with open("movie.csv", mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow(["Título", "Data de Lançamento", "Nota", "Sinopse"])

#Essa função serve para acessar o link de um repositorio de filme e extrair o seu conteudo HTML
def get_soup(movie_link):
    time.sleep(random.uniform(0, 0.02))
    try:
        response = requests.get(movie_link, headers=headers, timeout=20)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except Exception as e:
        print(f'Erro ao baixar {movie_link}: {e}')
        return None

def extract_movie_details(movie_soup: BeautifulSoup, movie_link):
    if not movie_soup:
        return
    
    #Esse trecho do codigo faz uma verificacao de seguranca pra garantir que a pagina carregou o conteudo esperado antes de extrair os dados
    detail_container = movie_soup.find("section", attrs={"data-testid": "movie-detail"})
    if detail_container is None: 
        print(f'Detalhe do filme nao encontrado: {movie_link}')
        return
    
    #Esse trecho do codigo pega a variavel e busca informaçoes especificas, uma busca restrita ao container
    title_tag = detail_container.find(attrs={"data-testid": "movie-title"})
    release_tag = detail_container.find(attrs={"data-testid": "movie-release"})
    rating_tag = detail_container.find(attrs={"data-testid": "movie-rating"})
    synopsis_tag = detail_container.find(attrs={"data-testid": "movie-synopsis"})

    #Esse bloco faz o tratamento e a limpeza dos dados, extrai os textos, remove os rotulos e guarda a informacao pura
    title = title_tag.get_text(strip=True) if title_tag else None
    date = release_tag.get_text(strip=True).replace("Lançamento:", "").strip() if release_tag else None
    rating = rating_tag.get_text(strip=True).replace("Nota:", "").strip() if rating_tag else None
    plot_text = synopsis_tag.get_text(strip=True).replace("Sinopse:", "").strip() if synopsis_tag else None
    
    #Esse bloco grava os dados no arquivo CSV
    if all([title, date, rating, plot_text]):
        with csv_lock:
            with open("movie.csv", mode="a", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                print(f"Salvo: {title} | {date} | {rating} | {plot_text}")
                writer.writerow([title, date, rating, plot_text])

#Essa funcao une o download da pagina com a extracao dos dados.
def process_single_movie(movie_link: str):
    movie_soup = get_soup(movie_link)
    if movie_soup:
        extract_movie_details(movie_soup, movie_link)

#Procura no HTML a tag <section> que possui o atributo data-testid="movies-list".
def extract_movies(soup: BeautifulSoup):
    container = soup.find("section", attrs={"data-testid": "movies-list"})

#mecanismo de seguranca se falhar
    if container is None:
        print("Container principal não encontrado.")
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(soup.prettify())
        return
#rocura todos os elementos <article> com data-testid="movie-item" contidos dentro do container.
    movies_table = container.find_all("article", attrs={"data-testid": "movie-item"})
    if not movies_table:
        print("Lista de filmes não encontrada.")
        return
# Percorre cada card de filme encontrado na lista,
# Procura a tag <a> com data-testid="movie-link, \
# Pega no atributo href (que é um caminho relativo como movie/1.html) e concatena com o domínio base
# ([https://havokkmorands.github.io/](https://havokkmorands.github.io/)), 
# gerando a URL completa para salvar na lista movie_links"

    movie_links = []
    for movie in movies_table:
        a_tag = movie.find("a", attrs={"data-testid": "movie-link"}, href=True)
        if a_tag:
            movie_links.append("https://havokkmorands.github.io/" + a_tag["href"])

    if not movie_links:
        print("Nenhum link de filme foi encontrado.")
        with open("debug_links.html", "w", encoding="utf-8") as f:
            f.write(container.prettify())
        return

    threads = min(MAX_THREADS, len(movie_links))
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        executor.map(process_single_movie, movie_links)


def main():
    start_time = time.time()

    popular_movies_url = "https://havokkmorands.github.io/movie-catalog/"
    response = requests.get(popular_movies_url, headers=headers, timeout=20)

    print("Status:", response.status_code)
    print("URL final:", response.url)

    soup = BeautifulSoup(response.content, "html.parser")
    extract_movies(soup)

    end_time = time.time()
    print("Total time taken:", end_time - start_time)

if __name__ == "__main__":
    main()