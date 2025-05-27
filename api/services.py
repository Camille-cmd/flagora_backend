from core.models import Country

from api.flag_store import flag_store

def get_random_flag():
    countries = Country.objects.order_by('?')

    data = {}
    for index, country in enumerate(countries):
        flag = country.flag
        if flag:
            with open(flag.path, 'r') as f:
                data[index] = f.read()

    return data
