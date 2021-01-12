import scrapy
import re
from scrapy.utils.project import get_project_settings

class HotelsSpider(scrapy.Spider):
    name = 'hotels'

    start_urls = ['https://www.booking.com/']
    
    def __init__(self, cities, **kwargs):
        self.cities = cities
        super().__init__(**kwargs)
    
    def parse(self, response):        
        # FormRequest used to make a search over cities
        for city_id, city in enumerate(self.cities):
            yield scrapy.FormRequest.from_response(
                response,
                formdata={'ss': city + ' France'},
                callback=self.after_search, 
                cb_kwargs=dict(city_id = city_id, city = city)
            )

    # Callback used after login
    def after_search(self, response, city_id, city):
        for hotel in response.xpath('//div[contains(@class, "sr_item")]'):
            score = hotel.xpath('.//div[contains(@class, "bui-review-score__badge")]/text()').get()
            nb_review = hotel.xpath('.//div[contains(@class, "bui-review-score__text")]/text()').get()
            
            # get distance and coordinate of accomodation
            coordinate = hotel.xpath('.//div[contains(@class, "sr_card_address_line")]')
            
            # lattitude and longitude
            longitude, lattitude = coordinate.xpath('.//a[contains(@class, "bui-link")]/@data-coords').get().split(",")

            # distance
            distance = coordinate.xpath('.//span[2]/text()').get()
            if distance:
                dist_extract = re.search(r"((?:\d{1,3}.)?\d{1,3}) (m|km)", distance.strip())
                distance_from_center = float(dist_extract.group(1))
                if dist_extract.group(2) == "km":
                    distance_from_center = 1000 * distance_from_center
            else: 
                distance_from_center = None
            
            # get type and ranking of hotel or accomodation
            quality = hotel.xpath('.//span[contains(@class, "c-accommodation-classification-rating")]')
            hotel_type = quality.xpath('./span[1]/@class').get()
            if hotel_type:
                hotel_type = "host" if "badge--tiles" in hotel_type else "hotel"
            ranking = quality.xpath('./span[1]/span[1]/@aria-label').get()
            
            yield {"city_id": city_id, 
                   "city": city, 
                   "name": hotel.xpath('.//span[contains(@class, "sr-hotel__name")]/text()').get().strip(),
                   "description": hotel.xpath('.//div[contains(@class, "hotel_desc")]/text()').get().strip(), 
                   "link": response.urljoin(hotel.xpath('.//a[contains(@class, "hotel_name_link")]/@href').get().strip()),
                   "score": float(score.strip().replace(",", ".")) if score else None, 
                   "nb_review": int(re.search(r"\d+", nb_review).group()) if nb_review else None, 
                   "distance_from_center": distance_from_center, 
                   "lattitude": float(lattitude), 
                   "longitude": float(longitude),
                   "type": hotel_type, 
                   "ranking": int(re.search(r"\d", ranking).group()) if ranking else None}
            
        # Select the NEXT button and store it in next_page
        next_page = response.urljoin(response.xpath('//a[contains(@class, "paging-next")]/@href').get())

        # Check if next_page exists
        if next_page is not None:
            # Follow the next page and use the callback parse
            yield response.follow(next_page, callback=self.after_search, cb_kwargs=dict(city_id = city_id, city = city))
