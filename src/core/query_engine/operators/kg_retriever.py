import logging
import json
import os
from src.core.embedding.text_preprocessor import TextPreprocessor
from src.core.query_engine.operators.base_operator import BaseOperator
from src.utils.cragapi_wrapper import CRAG
from src.utils.file_path import KG_RESULTS_FILE, QA_MUSIC_FUNCTION_TEMPLATE, QA_MOVIE_FUNCTION_TEMPLATE, QA_FINANCE_FUNCTION_TEMPLATE, QA_SPORT_FUNCTION_TEMPLATE, QA_OPEN_FUNCTION_TEMPLATE
from transformers import AutoTokenizer, LlamaForCausalLM
from datetime import datetime
import pytz

CRAG_MOCK_API_URL = os.getenv("CRAG_MOCK_API_URL", "http://127.0.0.1:8000")

class KGRetriever(BaseOperator):
    """
    Operator for retrieving data from the a knowledge graph in different domains.
    """

    def __init__(self, model_name = "meta-llama/Meta-Llama-3-8B-Instruct"):
        """
        Initialize the Retriever operator.
        :param model_name: The long-term memory instance to retrieve data from.
        """
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.llm = LlamaForCausalLM.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name) 

    def execute(self, input_data, **kwargs):
        """
        :param input_data: (query, query_time, domain_info).
        :param kwargs: Additional parameters (e.g., number of results).
        :return: Retrieved data.
        """
        try:
            query, query_time, domain = input_data[0]
            template_path = ""
            if domain == "music":
                template_path = QA_MUSIC_FUNCTION_TEMPLATE
                entities = self._extract_llm_function_call(query, query_time, template_path)
                results = self._get_kg_music_results(entities)
            elif domain == "movie":
                template_path = QA_MOVIE_FUNCTION_TEMPLATE
                entities = self._extract_llm_function_call(query, query_time, template_path)
                results = self._get_kg_movie_results(entities)
            elif domain == "finance":
                template_path = QA_FINANCE_FUNCTION_TEMPLATE
                entities = self._extract_llm_function_call(query, query_time, template_path)
                results = self._get_kg_finance_results(entities)
            elif domain == "sports":
                template_path = QA_SPORT_FUNCTION_TEMPLATE
                entities = self._extract_llm_function_call(query, query_time, template_path)
                results = self._get_kg_sports_results(entities)
            elif domain == "open":
                template_path = QA_OPEN_FUNCTION_TEMPLATE
                entities = self._extract_llm_function_call(query, query_time, template_path)
                results = self._get_kg_open_results(entities)
            if results:
                self.logger.info(f"Data retrieved successfully: {len(results)} result(s) found.")
                
                # Store kg_results in a file
                kg_results = ""
                for result in results:
                    kg_results += f"- {result.strip()}\n"

                file_path = KG_RESULTS_FILE
                try:
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(kg_results)
                    print(f"KG Results have been written to {file_path}")
                except IOError as e:
                    print(f"An error occurred while writing to the file: {e}")
                
                # Emit the raw query and results
                self.emit((query, query_time, results))
            else:
                self.logger.warning("No data found in long-term memory.")
        except Exception as e:
            self.logger.error(f"Error during retrieval: {str(e)}")
            raise RuntimeError(f"Retriever execution failed: {str(e)}")

    def _extract_llm_function_call(self, query, query_time, template_path):
        """
        Extract function calls from the generated output.
        :param query: The input query.
        :param query_time: The input query time.
        :param template_path: The path to the template file.
        :return: A list of extracted function calls.
        """
        formatted_prompts = self._format_prompts_for_function_call_extraction(query, query_time, template_path)
        inputs = self.tokenizer(formatted_prompts, return_tensors="pt")
        responses = self.llm.generate(
            **inputs,
            max_new_tokens=4096,  # Maximum number of tokens to generate per output sequence.
            do_sample=True,
            top_p=0.9,  # Float that controls the cumulative probability of the top tokens to consider.
            temperature=0.1,  # Randomness of the sampling
            num_return_sequences=1  # Number of output sequences to return for each prompt.
        )
        response_text = self.tokenizer.decode(responses[0], skip_special_tokens=True)
        
        entities = []
        entities = self._extract_entities(response_text)
        print(f"Generated Function calls: {entities}")
        return entities

    def _format_prompts_for_function_call_extraction(self, query, query_time, template_path=None):
        '''
        Format the prompts for function call extraction.
        :param query: The input query.
        :param query_time: The input query time.
        :param template_path: The path to the template file.
        :return: A list of formatted prompts.
        '''
        formatted_prompts = []
        template_path = template_path
        with open(template_path, "r") as file:
            Entity_MUSIC_Extract_TEMPLATE = file.read()
        user_message = ""
        user_message += f"Query: {query}\n"
        user_message += f"Query Time: {query_time}\n"
        formatted_prompts.append(
            self.tokenizer.apply_chat_template(
                [
                    {"role": "system", "content": Entity_MUSIC_Extract_TEMPLATE},
                    {"role": "user", "content": user_message},
                ],
                tokenize=False,
                add_generation_prompt=True,
            )
        )
        return formatted_prompts
    
    def _extract_entities(self, generated_output, decoder=json.JSONDecoder()):
        """
        Extract the JSON data from the generated output.
        :param generated_output: The full text generated by the model.
        :return: A list of extracted JSON objects or the full output if extraction fails.
        """
        # Extract the text after "assistant"
        if "assistant" in generated_output:
            text = generated_output.split("assistant")[1].strip()
            
        pos = 0
        results = []
        while True:
            match = text.find("{", pos)
            if match == -1:
                break
            try:
                result, index = decoder.raw_decode(text[match:])
                results.append(result)
                pos = match + index
            except ValueError:
                pos = match + 1
        return results
  
    def _convert_pt_to_est(self, query_time):
        """
        Convert Pacific Time (PT) to Eastern Time (EST).
        :params query_time (str): A string representing the time in Pacific Time, formatted as "%m/%d/%Y %H:%M:%S", e.g., "01/16/2025 12:00:00".
        :return: The converted time string in Eastern Time, formatted as "%Y-%m-%d %H:%M:00 EST".
        """
        # Parse the input time string
        datetime_obj = datetime.strptime(query_time[:-3], "%m/%d/%Y %H:%M:%S")
        
        # Define the time zones for Pacific Time and Eastern Time
        pt_zone = pytz.timezone('US/Pacific')
        est_zone = pytz.timezone('US/Eastern')
        
        # Localize the parsed time object to Pacific Time
        datetime_obj = pt_zone.localize(datetime_obj)
        
        # Convert the time object to Eastern Time
        datetime_obj_est = datetime_obj.astimezone(est_zone)
        
        # Format the output string as required
        formatted_datetime = datetime_obj_est.strftime("%Y-%m-%d %H:%M:00 EST")
        
        return formatted_datetime

    def _get_kg_music_results(self, entities):
        '''
        Retrieve data from the music domain.
        :param entities: A list of entities extracted from the generated output.
        :return: A list of retrieved data.
        '''
        api = CRAG(server=CRAG_MOCK_API_URL)
        batch_kg_results = []
        for entity in entities:
            kg_results = []
            res = ""
            print(entity.keys())
            # movie_domain
            func_name = entity["name"]
            params = entity["params"]
            if func_name == "get_artist_info":
                artist = params["artist_name"]
                artist_information = params["artist_information"]
                try:
                    # Only return the first entity
                    name = api.music_search_artist_entity_by_name(artist)["result"][0]
                    if artist_information in ["birthday"]:
                        res = api.music_get_artist_birth_date(name)["result"]
                    if artist_information in ["birthplace"]:
                        res = api.music_get_artist_birth_place(name)["result"]
                    if artist_information in ["lifespan"]:
                        res = api.music_get_lifespan(name)["result"]
                    if artist_information in ["all_works"]:
                        res = api.music_get_artist_all_works(name)["result"]
                    if artist_information in ["grammy_count"]:
                        res = api.music_grammy_get_award_count_by_artist(name)["result"]
                    if artist_information in ["grammy_year"]:
                        res = api.music_grammy_get_award_date_by_artist(name)["result"]
                    if artist_information in ["band_members"]:
                        res = api.music_get_members(name)["result"]
                    kg_results.append({artist + "_" + artist_information: res})
                except Exception as e:
                    self.logger.warning(f"Error in music_get_artist_info: {e}")
                    pass
            if func_name == "get_song_info":
                song_name = params["song_name"]
                song_aspect = params["song_aspect"]
                try:
                    # return top-10 most similar songs(simple to wrong)
                    names = api.music_search_song_entity_by_name(song_name)["result"]
                    for name in names:
                        # 单个属性
                        if song_aspect in ["author"]:
                            res = api.music_get_song_author(name)["result"]
                        if song_aspect in ["grammy_award_count"]:
                            res = api.music_grammy_get_award_count_by_song(name)["result"]
                        if song_aspect in ["release_country"]:
                            res = api.music_get_song_release_country(name)["result"]
                        if song_aspect in ["release_date"]:
                            res = api.music_get_song_release_date(name)["result"]
                        kg_results.append({name + "_" + song_aspect: res})
                except Exception as e:
                    self.logger.warning(f"Error in music_get_song_info: {e}")
                    pass
            if func_name == "get_year_info":
                year = params["year"]
                year_aspect = params["year_aspect"]
                try:
                    # convert year to int
                    year = int(year)
                    if year_aspect in ["grammy_get_best_song"]:
                        res = api.music_grammy_get_best_song_by_year(year)["result"]
                    if year_aspect in ["grammy_get_best_album"]:
                        res = api.music_grammy_get_best_album_by_year(year)["result"]
                    if year_aspect in ["grammy_get_best_artist"]:
                        res = api.music_grammy_get_best_artist_by_year(year)["result"]    
                    kg_results.append({str(year) + "_" + year_aspect: res})
                except Exception as e:
                    self.logger.warning(f"Error in music_get_year_info: {e}")
                    pass
            if func_name == "get_billboard_rank_date": 
                rank = params["rank"]
                date = params.get("date")  # 使用 get 方法，如果 date 不存在则返回 None
                if not date:
                    date = None
                try:
                    res = api.music_get_billboard_rank_date(rank, date)["result"]
                    kg_results.append({f"{date} Billboard rank {rank}": {"songs": res[0], "artists": res[1]}})
                except Exception as e:
                    self.logger.warning(f"Error in get_billboard_rank_date: {e}")
                    pass
            if func_name == "get_billboard_attributes":
                date = params["date"]
                attribute = params["attribute"]
                song_name = params["song_name"]
                try:
                    res = api.music_get_billboard_attributes(date, attribute, song_name)["result"]
                    kg_results.append({f"{date} Billboard {attribute} of {song_name}": res})
                except Exception as e:
                    self.logger.warning(f"Error in get_billboard_attributes: {e}")
                    pass
            batch_kg_results.append("<DOC>\n".join([str(res) for res in kg_results]) if len(kg_results) > 0 else "")
        return batch_kg_results

    def _get_kg_movie_results(self, entities):
        '''
        Retrieve data from the movie domain.
        :param entities: A list of entities extracted from the generated output.
        :return: A list of retrieved data.
        '''
        api = CRAG(server=CRAG_MOCK_API_URL)
        batch_kg_results = []
        for entity in entities:
            kg_results = []
            res = ""
            print(entity.keys())
            # movie_domain
            func_name = entity["name"]
            params = entity["params"]
            if func_name == "get_person_info":
                person = params["person_name"]
                person_aspect = params["person_aspect"]
                try:
                    # NOTE: 测试时发现不一定能找到directed_movies
                    data = api.movie_get_person_info(person)["result"][0]
                    if person_aspect in ["oscar_awards", "birthday"]:
                        res = data[person_aspect]
                        kg_results.append({person + "_" + person_aspect: res})
                    if person_aspect in ["acted_movies", "directed_movies"]:
                        movie_info = []
                        for movie_id in data[person_aspect]:
                            movie_info.append(api.movie_get_movie_info_by_id(movie_id)["result"])
                        kg_results.append({person + "_" + person_aspect: movie_info})
                except Exception as e:
                    kg_results.append({person + "_" + person_aspect: ""})
                    self.logger.warning(f"Error in movie_get_person_info: {e}")
                    pass
            if func_name == "get_movie_info":
                movie_name = params["movie_name"]
                movie_aspect = params["movie_aspect"]
                try:
                    data = api.movie_get_movie_info(movie_name)["result"][0]
                    # 单个属性
                    if movie_aspect in ["title", "release_date", "original_title", "original_language", "budget", "revenue", "rating", "genres", "oscar_awards", "crew"]:
                        res = data[movie_aspect]
                        kg_results.append({movie_name + "_" + movie_aspect: res})
                    if movie_aspect in ["cast"]:
                        res = data[movie_aspect]
                        # TODO: gender
                        kg_results.append({movie_name + "_" + movie_aspect: res})
                except Exception as e:
                    self.logger.warning(f"Error in movie_get_movie_info: {e}")
                    pass
            if func_name == "get_year_info":
                year = params["year"]
                year_aspect = params["year_aspect"]
                try:
                    data = api.movie_get_year_info(year)["result"]
                    if year_aspect in ["movie_list"]:
                        movie_info = []
                        for movie_id in data[year_aspect]:
                            movie_info.append(api.movie_get_movie_info_by_id(movie_id)["result"])
                        kg_results.append({year + "_" + year_aspect: movie_info})
                    if year_aspect in ["oscar_awards"]:
                        res = data[year_aspect]
                        kg_results.append({year + "_" + year_aspect: res})
                except Exception as e:
                    self.logger.warning(f"Error in movie_get_year_info: {e}")
                    pass
            batch_kg_results.append("<DOC>\n".join([str(res) for res in kg_results]) if len(kg_results) > 0 else "")
        return batch_kg_results 

    def _get_kg_finance_results(self, entities):
        '''
        Retrieve data from the finance domain.
        :param entities: A list of entities extracted from the generated output.
        :return: A list of retrieved data.
        '''
        api = CRAG(server=CRAG_MOCK_API_URL)
        batch_kg_results = []
        for entity in entities:
            kg_results = []
            tickers = []
            res = ""
            # finance_domain
            func_name = entity["name"]
            params = entity["params"]
            if func_name == "get_finance_info":
                market_identifier = params["market_identifier"]
                metric = params["metric"]
                query_time = params["datetime"]
                try:
                    # convert query_time to datetime
                    formatted_datetime = self._convert_pt_to_est(query_time)
                    # extract stock codes by company name
                    companys = api.finance_get_company_name(market_identifier)["result"]
                    for company in companys:
                        data = api.finance_get_ticker_by_name(company)["result"]
                        if data:
                            tickers.append(data)
                            kg_results.append({company +"_ticker_name": data})   
                    tickers.append(market_identifier)
                    for ticker in tickers:
                        try:
                            res = ""
                            if metric in ["price"]:
                                price_history = []
                                price_history = api.finance_get_detailed_price_history(ticker)["result"]
                                if formatted_datetime in price_history:
                                    res = price_history[formatted_datetime]
                                else:
                                    price_history = api.finance_get_price_history(ticker)["result"]
                                    if formatted_datetime in price_history:
                                        res = price_history[formatted_datetime]
                                if not res:
                                    data_list = list(price_history.items())
                                    top_100_records = data_list[:100]
                                    res = dict(top_100_records)
                                    # print(res)
                                    # res = price_history[:100]
                            if metric in ["dividend"]:
                                price_history = api.finance_get_dividends_history(ticker)["result"]
                                if formatted_datetime in price_history:
                                    res = price_history[formatted_datetime]
                                if not res:
                                    data_list = list(price_history.items())
                                    top_100_records = data_list[:100]
                                    res = dict(top_100_records)
                            if metric in ["P/E ratio"]:
                                res = api.finance_get_pe_ratio(ticker)["result"]
                            if metric in ["EPS"]:
                                res = api.finance_get_eps(ticker)["result"]
                            if metric in ["marketCap"]:
                                res = api.finance_get_market_capitalization(ticker)["result"]
                            if metric in ["other"]:
                                res = api.finance_get_info(ticker)["result"]
                            kg_results.append({formatted_datetime +  "_" + ticker + "_" + metric: res})
                        except Exception as e:
                            self.logger.warning(f"Error in finance_get_finance_info: {e}")
                            pass
                except Exception as e:
                    self.logger.warning(f"Error in get_finance_info: {e}")
                    pass
            batch_kg_results.append("<DOC>\n".join([str(res) for res in kg_results]) if len(kg_results) > 0 else "")
        return batch_kg_results
    
    def _get_kg_sports_results(self, entities):
        '''
        Retrieve data from the sports domain.
        :param entities: A list of entities extracted from the generated output.
        :return: A list of retrieved data.
        '''
        api = CRAG(server=CRAG_MOCK_API_URL)
        batch_kg_results = []
        for entity in entities:
            kg_results = []
            res = ""
            func_name = entity["name"]
            params = entity["params"]
            if func_name == "get_soccer_games_on_date":
                date = params["date"]
                team_name = params.get("team_name")
                try:
                    res = api.sports_soccer_get_games_on_date(date, team_name)["result"]
                    if team_name:
                        kg_results.append({date + "_soccer_games_" + team_name: res})
                    else:
                        kg_results.append({date + "_soccer_games": res})
                except Exception as e:
                    self.logger.warning(f"Error in sports_get_soccer_games_on_date: {e}")
                    pass
            if func_name == "get_nba_games_on_date":
                date = params["date"]
                team_name = params.get("team_name")
                try:
                    res = api.sports_nba_get_games_on_date(date, team_name)["result"]
                    if team_name:
                        kg_results.append({date + "_nba_games_" + team_name: res})
                    else:
                        kg_results.append({date + "_nba_games": res})
                except Exception as e:
                    self.logger.warning(f"Error in sports_get_nba_games_on_date: {e}")
                    pass
            if func_name == "get_play_by_play_data_by_game_ids":
                game_ids = params["game_ids"]
                try:
                    res = api.sports_nba_get_play_by_play_data_by_game_ids(game_ids)["result"]
                    kg_results.append({"get_play_by_play_data": res})
                except Exception as e:
                    self.logger.warning(f"Error in sport_get_play_by_play_data_by_game_ids: {e}")
            batch_kg_results.append("<DOC>\n".join([str(res) for res in kg_results]) if len(kg_results) > 0 else "")
        return batch_kg_results
    
    def _get_kg_open_results(self, entities):
        '''
        Retrieve data from the open domain.
        :param entities: A list of entities extracted from the generated output.
        :return: A list of retrieved data.
        '''
        api = CRAG(server=CRAG_MOCK_API_URL)
        batch_kg_results = []
        for entity in entities:
            kg_results = []
            func_name = entity["name"]
            param = entity["params"]
            if func_name == "get_entity_details":
                entity_name = param["entity_name"]
                try:
                    # Only return the first entity
                    name = api.open_search_entity_by_name(entity_name)["result"][0]
                    res = api.open_get_entity(name)["result"]
                    kg_results.append({name: res})
                except Exception as e:
                    self.logger.warning(f"Error in open_get_entity_details: {e}")
                    pass
            batch_kg_results.append("<DOC>\n".join([str(res) for res in kg_results]) if len(kg_results) > 0 else "")
        return batch_kg_results
