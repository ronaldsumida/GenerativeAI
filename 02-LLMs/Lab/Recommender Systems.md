# Hands-on lab: Text-based recommender systems

A branch of machine learning that has proven its mettle in recent years is recommender systems – systems that recommend products or services to customers. Amazon's recommender system reportedly [drives 35% of its sales](https://evdelo.com/amazons-recommendation-algorithm-drives-35-of-its-sales/). The good news is that you don't have to be Amazon to benefit from a recommender system, nor do you have to have Amazon's resources to build one. They're relatively simple to create once you learn a few basic principles.

Recommender systems come in many forms. Popularity based systems present options to customers based on what products and services are popular at the time – for example, "Here are this week's bestsellers." Collaborative systems make recommendations based on what others have selected, as in "People who bought this book also bought these books." Neither of these systems requires machine learning.

Content-based systems, by contrast, benefit greatly from machine learning. An example of a content-based system is one that says "if you bought this book, you might like these books also." Such systems require a means for quantifying similarity between items. If you like the movie *Die Hard*, you might or might not like *Monty Python and the Holy Grail*. If you like *Toy Story*, you'll probably like *A Bug's Life*, too. But how do you make that determination mathematically?

Content-based recommenders require two ingredients: a way to vectorize (convert to numbers) the attributes that characterize a service or product, and a means for calculating similarity between the resulting vectors. The first one is easy. `CountVectorizer` converts text into tables of word counts and can be used to vectorize text characterizing movies. The second can be accomplished using [cosine similarity](https://en.wikipedia.org/wiki/Cosine_similarity). Let's combine the two to create a model that recommends movies based on other movies that you like.

![](Images/movies.png)

<a name="Exercise1"></a>
## Exercise 1: Vectorize movie data and compute cosine similarities

In this exercise, you'll load a dataset containing information about more than 4,800 movies, including title, budget, genres, keywords, and cast. You will then combine information from several of the dataset's textual columns, use `CountVectorizer` to vectorize the resulting text, and use Scikit's [`cosine_similarity`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.cosine_similarity.html) function to compute cosine similarities for each movie pair.

1. A dataset named **movies.csv** is provided for you in the "Data" folder of this lab. Copy it into the "Data" folder where your Jupyter notebooks are hosted. Then run the following statements in a Jupyter notebook to load the dataset and show the first five rows:

	```python
	import pandas as pd
	
	df = pd.read_csv('Data/movies.csv')
	df.head()
	```

1. The dataset contains 24 columns, only a few of which are needed to describe a movie. Use the following statements to extract key columns such as "title" and "genres" and fill missing values with empty strings:

	```python
	df = df[['title', 'genres', 'keywords', 'cast', 'director']]
	df = df.fillna('') # Fill missing values with empty strings
	df.head()
	```

1. Next, add a column named "features" that combines all the words in the other columns:

	```python
	df['features'] = df['title'] + ' ' + df['genres'] + ' ' + df['keywords'] + ' ' + df['cast'] + ' ' + df['director']
	```

1. Use `CountVectorizer` to vectorize the text in the "features" column:

	```python
	from sklearn.feature_extraction.text import CountVectorizer
	
	vectorizer = CountVectorizer(stop_words='english', min_df=20)
	word_matrix = vectorizer.fit_transform(df['features'])
	word_matrix.shape
	```

1. The table of word counts contains 4,803 rows – one for each movie – and 918 columns. The next task is to compute cosine similarities for each row pair:

	```python
	from sklearn.metrics.pairwise import cosine_similarity
	
	sim = cosine_similarity(word_matrix)
	```

What are the dimensions of the resulting similarity matrix? If you're not sure, type `sim.shape` into the next cell to find out.

<a name="Exercise2"></a>
## Exercise 2: Use the similarity matrix to pick movies

The goal of building a recommender system for movies is to input a movie title and identify the *n* movies that are most similar to the one you input. In this exercise, you'll write a function that does that using the similarity matrix generated in the previous exercise. Then you'll use the function to recommend some movies.

1. Define a function named `get_recommendations` that accepts a movie title, a `DataFrame` containing information about all the movies, a similarity matrix, and the number of movie titles to return:

	```python
	def get_recommendations(title, df, sim, count=10):
	    # Get the row index of the specified title in the DataFrame
	    index = df.index[df['title'].str.lower() == title.lower()]
	
	    # Return an empty list if there is no entry for the specified title
	    if (len(index) == 0):
	        return []
	
	    # Get the corresponding row in the similarity matrix
	    similarities = list(enumerate(sim[index[0]]))
	
	    # Sort the similarity scores in that row in descending order
	    recommendations = sorted(similarities, key=lambda x: x[1], reverse=True)
	
	    # Get the top n recommendations, ignoring the first entry in the list since
	    # it corresponds to the title itself (and thus has a similarity of 1.0)
	    top_recs = recommendations[1:count + 1]
	
	    # Generate a list of titles from the indexes in top_recs
	    titles = []
	
	    for i in range(len(top_recs)):
	        title = df.iloc[top_recs[i][0]]['title']
	        titles.append(title)
	
	    return titles
	```

	This function sorts the cosine similarities in descending order to identify the `count` movies most like the one identified by the `title` parameter. Then it returns the titles of those movies.

1. Now use `get_recommendations` to search the database for similar movies. First ask for the 10 movies that are most similar to the James Bond thriller *Skyfall*:

	```python
	get_recommendations('Skyfall', df, sim)
	```

1. Call `get_recommendations` again to list movies that are like *Mulan*:

	```python
	get_recommendations('Mulan', df, sim)
	```

1. Feel free to try other movies as well. Note that you can only input movie titles that are in the dataset. Use the following statements to print a complete list of titles:

	```python
	pd.set_option('display.max_rows', None)
	print(df['title'])
	```

I think you'll agree that the system does a pretty credible job of picking similar movies. Not bad for about 20 lines of code!