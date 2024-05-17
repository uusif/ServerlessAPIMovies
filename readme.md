
# Serverless Movies API
Capstone project using cloud infrastructure to build 3 functions using Cosmo NOSQL db, cloud storage and serverless function. This was deployed onto Azure Functions.

# Technologies Used
* Python
* Azure Functions 
* CosmoDB
* Azure Blob storage
* OpenAI (for movie summary generation)

# Instructions
* Ensure all neccessary packages are installed in order to run the functions, this includes: Azure Cosmos, Azure Functions, OpenAI, json, and os. All packages can be found in the requirements.txt file

# Functions
When developing the 3 functions, I had created the individual functions to test within Python first. Then, I created functions that would call the original function via HTTP Request.
````Python
#getMovies() returns all movies available
def getMovies():
    movie_list = []
    for item in container.query_items(query='SELECT  c.title, c.releaseYear, c.genre, c.coverUrl From c', enable_cross_partition_query=True):
        movie_list.append(item)
    return(json.dumps(movie_list, indent=True))

#getMoviesByYear(year) returns all movies within the specified year. User specifies the year.
def getMoviesByYear(year):
    movie_list = []
    for item in container.query_items(query = f'SELECT c.title, c.releaseYear, c.genre, c.coverUrl From c WHERE c.releaseYear = {year}', enable_cross_partition_query=True):
        movie_list.append(item)
    return json.dumps(movie_list, indent = True)

#generate_summary to generate the summary for the selected movie
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

#getMoviesBySummary(title) user inputs the movie and the generated summary is included as a part of the data
def getMoviesBySummary(title):
    movie_list = []
    for item in container.query_items(query = f'SELECT c.title, c.releaseYear, c.genre, c.coverUrl From c WHERE LOWER(c.title) = @title', parameters = [dict(name='@title', value = title.lower())], enable_cross_partition_query=True):
        movie_summary = generate_summary(item['title'])
        item['generatedSummary'] = movie_summary
        movie_list.append(item)
    return json.dumps(movie_list, indent = True)
````

These functions are then called in HttpRequests. I could have also just built the functions within the HttpRequest, but I found that testing it in Python first before building the API allowed me to better grasp the concept and ensure I was moving in the right direction.
````Python
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
````

# Testing
To ensure that our APIs would work once deployed to Azure, we would need to test our functions locally. This documentation provides instructions that you would need to test your functions locally before deployment: [here](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=macos%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-python)

# Output 
Once published, you will be provided with 3 URLs in which your functions can be invoked:

Get Movies
https://movedemo3.azurewebsites.net/api/getmovies

Get Movies By Year
https://movedemo3.azurewebsites.net/api/getmoviesbyyear/{year}

Get Movie Summary
https://movedemo3.azurewebsites.net/api/getmoviesummary/{title}

# Considerations
* When testing locally, our functions worked fine. Once deployed to Azure there were some changes that need to be made. In my case, my CosmoDB credentials were not being read correctly.
* Ensure your CosmoDB, Resource Groups, Function App and storage accounts are set up correctly with the right permissions
* I would look to add onto this project and develop a website using the APIs in the future# Serverless-Movie-API
