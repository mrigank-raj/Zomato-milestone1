import os
import csv
import logging
import requests
import pandas as pd
from app.domain.models import Restaurant
from app.infrastructure.config import AppConfig

# Increase CSV field size limit to handle very long reviews_list
csv.field_size_limit(10000000)

logger = logging.getLogger("zomato-rec")

class DatasetLoader:
    def __init__(self, config: AppConfig):
        self.config = config
        self.dataset_url = "https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation/resolve/main/zomato.csv"

    def load(self) -> list[Restaurant]:
        """
        Loads the preprocessed Zomato dataset. If a local cache exists, it loads from cache.
        Otherwise, it streams the dataset directly from Hugging Face, cleans it, caches it,
        and returns the list of Restaurant objects.
        """
        cache_path = self.config.dataset_cache_path
        
        # 1. Try loading from cache
        if cache_path and os.path.exists(cache_path):
            logger.info(f"Loading dataset from cache: {cache_path}")
            try:
                if cache_path.endswith('.parquet'):
                    df = pd.read_parquet(cache_path)
                elif cache_path.endswith('.csv'):
                    import ast
                    df = pd.read_csv(cache_path)
                    # Convert stringified lists and dicts back to Python objects
                    df['cuisines'] = df['cuisines'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
                    df['raw'] = df['raw'].apply(lambda x: ast.literal_eval(x) if isinstance(x, str) else x)
                else:
                    raise ValueError(f"Unsupported cache file extension: {cache_path}")
                return self._df_to_restaurants(df)
            except Exception as e:
                logger.error(f"Error loading from cache: {e}. Will attempt to rebuild cache.")
                # Fall back to rebuild

        # 2. Download and prepare from URL (streaming to save disk space)
        logger.info("Local cache not found. Rebuilding dataset by streaming from Hugging Face...")
        try:
            restaurants = self._stream_and_preprocess()
            
            # Save cache if cache path is configured
            if cache_path:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                df = pd.DataFrame([self._restaurant_to_dict(r) for r in restaurants])
                if cache_path.endswith('.parquet'):
                    df.to_parquet(cache_path)
                elif cache_path.endswith('.csv'):
                    df.to_csv(cache_path, index=False)
                logger.info(f"Successfully cached preprocessed dataset to {cache_path}")
                
            return restaurants
        except Exception as e:
            logger.error(f"Failed to load or process dataset: {e}")
            raise

    def _stream_and_preprocess(self) -> list[Restaurant]:
        logger.info(f"Streaming from URL: {self.dataset_url}")
        
        response = requests.get(self.dataset_url, stream=True)
        response.raise_for_status()
        
        def line_generator():
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    yield line

        reader = csv.DictReader(line_generator())
        
        restaurants = []
        count = 0
        skipped = 0
        
        for row in reader:
            if count >= 30000:
                break
            name = row.get('name')
            location = row.get('location')
            
            if not name or not location:
                skipped += 1
                continue
                
            # Parse rating
            rate_str = row.get('rate', '0.0')
            try:
                if rate_str and '/' in rate_str:
                    rating = float(rate_str.split('/')[0].strip())
                else:
                    rating = 0.0
            except (ValueError, TypeError):
                rating = 0.0
                
            # Parse cost
            cost_str = row.get('approx_cost(for two people)', '')
            try:
                if cost_str:
                    cost_clean = ''.join(c for c in str(cost_str) if c.isdigit())
                    cost_for_two = int(cost_clean) if cost_clean else None
                else:
                    cost_for_two = None
            except (ValueError, TypeError):
                cost_for_two = None
                
            # Cuisines
            cuisines_str = row.get('cuisines', '')
            if cuisines_str:
                cuisines = [c.strip() for c in cuisines_str.split(',') if c.strip()]
            else:
                cuisines = []
                
            # Votes
            votes_str = row.get('votes', '0')
            try:
                votes = int(votes_str) if votes_str else 0
            except (ValueError, TypeError):
                votes = 0
                
            r_id = str(count)
            
            # Map raw fields needed for debugging/future extensions
            raw_fields = {
                'address': row.get('address'),
                'online_order': row.get('online_order'),
                'book_table': row.get('book_table'),
                'rest_type': row.get('rest_type'),
                'dish_liked': row.get('dish_liked'),
                'menu_item': row.get('menu_item'),
                'listed_in_type': row.get('listed_in(type)'),
                'listed_in_city': row.get('listed_in(city)'),
            }
            
            restaurant = Restaurant(
                id=r_id,
                name=name.strip(),
                location=location.strip(),
                cuisines=cuisines,
                rating=rating,
                cost_for_two=cost_for_two,
                address=row.get('address', '').strip() if row.get('address') else None,
                votes=votes,
                raw=raw_fields
            )
            restaurants.append(restaurant)
            count += 1
            
            if count % 10000 == 0:
                logger.info(f"Streamed and preprocessed {count} restaurants...")
                
        logger.info(f"Streaming complete. Preprocessed {count} restaurants (skipped {skipped}).")
        return restaurants

    def _restaurant_to_dict(self, r: Restaurant) -> dict:
        return {
            'id': r.id,
            'name': r.name,
            'location': r.location,
            'cuisines': r.cuisines,
            'rating': r.rating,
            'cost_for_two': r.cost_for_two,
            'address': r.address,
            'votes': r.votes,
            'raw': r.raw
        }

    def _df_to_restaurants(self, df: pd.DataFrame) -> list[Restaurant]:
        restaurants = []
        for _, row in df.iterrows():
            # Handle list storage in parquet (sometimes read back as numpy array or list)
            cuisines = row['cuisines']
            if hasattr(cuisines, 'tolist'):
                cuisines = cuisines.tolist()
            elif not isinstance(cuisines, list):
                cuisines = list(cuisines) if cuisines is not None else []
                
            restaurants.append(
                Restaurant(
                    id=str(row['id']),
                    name=str(row['name']),
                    location=str(row['location']),
                    cuisines=cuisines,
                    rating=float(row['rating']),
                    cost_for_two=int(row['cost_for_two']) if pd.notna(row['cost_for_two']) else None,
                    address=str(row['address']) if pd.notna(row['address']) else None,
                    votes=int(row['votes']) if pd.notna(row['votes']) else 0,
                    raw=dict(row['raw']) if isinstance(row['raw'], dict) else {}
                )
            )
        return restaurants
