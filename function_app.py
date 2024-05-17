import logging
import os
import requests
import json
from dotenv import load_dotenv
load_dotenv()
from azure.cosmos import CosmosClient
import azure.functions as func
import openai

app = func.FunctionApp()


# database information

#cosmo nosql db client
client = CosmosClient.from_connection_string(os.environ['CosmosDbConnectionSetting'])
#calling database
database = client.get_database_client(os.environ['DBNAME'])
#calling container within the database
container = database.get_container_client(os.environ['CONTNAME'])

#openAI API
api_key = os.getenv('openaiapikey')
openai.api_key = api_key

#function 1: return a json list of all movies in your DB. created this function initially to test this function. we will be calling this function in our HttpRequest
def getMovies():
    movie_list = []
    for item in container.query_items(query='SELECT  c.title, c.releaseYear, c.genre, c.coverUrl From c', enable_cross_partition_query=True):
        movie_list.append(item)
    return(json.dumps(movie_list, indent=True))

# # #function 2: create a function that returns a list of movies by year. User selects the year. we will be calling this function in our HttpRequest

def getMoviesByYear(year):
    movie_list = []
    for item in container.query_items(query = f'SELECT c.title, c.releaseYear, c.genre, c.coverUrl From c WHERE c.releaseYear = {year}', enable_cross_partition_query=True):
        movie_list.append(item)
    return json.dumps(movie_list, indent = True)

# #function 3: user selects a movie. output is a json list with additional field called generatedSummary which uses openAI API to generate a summary for the movie. the first function generates the summary while the second function allows the user to input the movie and output the generated summary along with all other data. we will call this function in our HttpRequest

#function to generate the summary for the selected movie
def generate_summary(movie_name):
    response = openai.chat.completions.create(
        model = "gpt-3.5-turbo",
        messages=[
            {"role":"user", "content": f"Summarize the movie: {movie_name} in 2 sentences"}
            ],
        temperature=1,
        max_tokens = 200,
    )
    return response.choices[0].message.content

#generate the data. user inputs the movie and the generated summary is included as a part of the data
def getMoviesBySummary(title):
    movie_list = []
    for item in container.query_items(query = f'SELECT c.title, c.releaseYear, c.genre, c.coverUrl From c WHERE LOWER(c.title) = @title', parameters = [dict(name='@title', value = title.lower())], enable_cross_partition_query=True):
        movie_summary = generate_summary(item['title'])
        item['generatedSummary'] = movie_summary
        movie_list.append(item)
    return json.dumps(movie_list, indent = True)

#API SET UP
# first API - this API is calling our getMovies() function. user just inputs the URL into their browser and it will return all movies in the database.
@app.function_name('getMovies')
@app.route(route="getMovies", auth_level=func.AuthLevel.ANONYMOUS)
def main(req: func.HttpRequest) -> func.HttpResponse:
    movie_list = getMovies()
    if movie_list:
        movie_data = json.loads(movie_list)
        formatted_movie_list = json.dumps(movie_data, indent = 4)
        return func.HttpResponse(
            body = formatted_movie_list,
            mimetype="application/json",
            status_code = 200
        )
    else:
        return func.HttpResponse(
            "No movies found",
            status_code= 404
        )

# second API - this API is calling our getMoviesByYear() function. user inputs the URL into their browser along with year and this returns all movies in the database with the year. If no movie exists for that year then it returns "No movies found for the specified year".
@app.function_name('getMoviesByYear')
@app.route(route='getMoviesByYear/{year}',auth_level=func.AuthLevel.ANONYMOUS)
def main(req:func.HttpRequest) -> func.HttpResponse:
    year = req.route_params.get('year')
    if year:
        try:
            year_str = "'"+year+"'"
        except ValueError:
            return func.HttpResponse("invalid year parameter. Please provide a valid year parameter", status_code=404)
        movie_list = getMoviesByYear(year_str)
        if len(movie_list) == 2 :
            return func.HttpResponse(
                "No movies found for the specified year",
                 status_code=200)
        else:
            return func.HttpResponse(
                body = movie_list,
                mimetype="application/json",
                status_code=200
            )
            
#third API - this API calls our getMovieSummary() function. user inputs the movie name into the URL and it outputs the movie, data points and a generated summary field with an AI generated summary using openAI API
@app.function_name('getMovieSummary')
@app.route(route='getMovieSummary/{title}',auth_level=func.AuthLevel.ANONYMOUS)
def main(req:func.HttpRequest) -> func.HttpResponse:
    title = req.route_params.get('title')
    movie_list = getMoviesBySummary(title)
    if len(movie_list) == 2 :
        return func.HttpResponse(
            "No movies found under specified title",
            status_code=200
        )
    else:
        return func.HttpResponse(
            body = movie_list,
            mimetype="application/json",
            status_code=200
        )
