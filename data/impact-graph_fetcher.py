from urllib2 import Request, urlopen
import json
import math
import settings

def fetch_popular_movies(since_year = 2010, limit = 100):
	page = 1
	options = [
		settings.api_key,
		settings.min_vote_avg,
		since_year,
		page,
	]

	movies = []
	while limit > 0:
		request = Request('http://api.themoviedb.org/3/discover/movie?api_key={}&sort_by=popularity.desc&vote_average.gte={}&primary_release_year.gte={}&page={}'.format(*options),
					  	  headers=settings.headers)
		response_body = urlopen(request).read()
		response_json = json.loads(response_body)
		movies += response_json["results"][:limit]
		limit -= len(response_json["results"])
		options[3] += 1
	return movies

def fetch_crew_for_movies(movies):
	people = []
	for movie in movies:
		mid = movie['id']
		options = [
			mid,
			settings.api_key,
		]
		request = Request('http://api.themoviedb.org/3/movie/{}?api_key={}&append_to_response=credits'.format(*options),
					  	  headers=settings.headers)
		response_body = urlopen(request).read()
		response_json = json.loads(response_body)
		movie['credits'] = response_json['credits']
	return movies;

def _get_people_node(graph, pid_to_node, people):
	node = None
	if people is None:
		return node

	if people['id'] in pid_to_node:
		pid = pid_to_node[people['id']]
		node = graph['nodes'][pid]
	else:
		pid = len(graph['nodes'])
		pid_to_node[people['id']] = pid
	return node

def _construct_connexe_component(graph):
	connected_nodes = []
	for link in graph['links']:
		last_set = None
		for s in connected_nodes:
			if link['source'] in s or link['target'] in s:
				s.add(link['source'])
				s.add(link['target'])
				if last_set is not None:
					s.update(last_set)
					connected_nodes.remove(last_set)
				last_set = s
		if last_set is None:
			connected_nodes.append(set([link['source'], link['target']]))
	print connected_nodes
	for i in xrange(len(connected_nodes)):
		for index in connected_nodes[i]:
			graph['nodes'][index]['connected_group'] = i


def movies_to_graph(movies, output_file):
	graph = {}
	graph['nodes'] = []
	graph['links'] = []

	pid_to_node = {}

	for movie in movies:
		mid = len(graph['nodes'])
		graph['nodes'].append({'id': movie['id'],
							   'popularity': movie['popularity'],
							   'name': movie['title'],
							   'connected_group': -1, # default connected component.
							   'vote_average': movie['vote_average']*4,
							   'group': settings.groups_node['Movie']})
		for people in movie['credits']['cast'][:settings.related_actors_number]:
			node = _get_people_node(graph, pid_to_node, people)
			if node is None:
				node = {'id': people['id'],
					   'name': people['name'],
					   'popularity': math.sqrt(movie['popularity']),
					   'connected_group': -1, # default connected component.
					   'vote_average': movie['vote_average'],
					   'group': settings.groups_node['Actor']}
				graph['nodes'].append(node)
			else:
				node['popularity'] += math.sqrt(movie['popularity'])
				node['vote_average'] += movie['vote_average']/2
			graph['links'].append({'source':pid_to_node[node['id']], 'target':mid, 'group': settings.groups_link['Acting']})

		if len(movie['credits']['crew']) == 0:
			continue
		first_crew = movie['credits']['crew'][0]
		director = first_crew if first_crew['job'] == 'Director' else None
		if director is None:
			continue
		node = _get_people_node(graph, pid_to_node, director)
		if node is None:
			node = {'id':director['id'],
				   'name': director['name'],
				   'popularity': math.sqrt(movie['popularity']),
				   'connected_group': -1, # default connected component.
				   'vote_average': movie['vote_average'],
				   'group': settings.groups_node['Director']}
			graph['nodes'].append(node)
		else:
			node['popularity'] += math.sqrt(movie['popularity'])
			node['vote_average'] += movie['vote_average']/2
		graph['links'].append({'source':pid_to_node[node['id']], 'target':mid, 'group': settings.groups_link['Directing']})

	_construct_connexe_component(graph)
	json.dump(graph, output_file, indent=4)


movies = fetch_popular_movies(settings.since_year, settings.fetch_popular_movies)
fetch_crew_for_movies(movies)

with open('graph.json', 'w') as f:
	movies_to_graph(movies, f)
	f.close()
