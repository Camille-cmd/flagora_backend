import factory.fuzzy
from django.core.files.uploadedfile import SimpleUploadedFile
from factory.django import DjangoModelFactory
from faker import Faker

faker_fr = Faker("fr_FR")
faker_en = Faker("en_US")


class UserFactory(DjangoModelFactory):
    class Meta:
        model = "core.User"

    username = factory.LazyAttribute(lambda _: faker_fr.name())
    password = factory.PostGenerationMethodCall("set_password", "<PASSWORD>")


class CityFactory(DjangoModelFactory):
    class Meta:
        model = "core.City"

    name_fr = factory.LazyAttribute(lambda _: faker_fr.city())
    name_en = factory.LazyAttribute(lambda _: faker_en.city())


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = "core.Country"

    name_fr = factory.LazyAttribute(lambda _: faker_fr.country())
    name_en = factory.LazyAttribute(lambda _: faker_en.country())
    iso2_code = factory.LazyAttribute(lambda _: faker_fr.country_code(representation="alpha-2"))
    iso3_code = factory.LazyAttribute(lambda _: faker_fr.country_code(representation="alpha-3"))
    continent = factory.LazyAttribute(lambda _: faker_fr.country())
    flag = factory.LazyAttribute(
        lambda _: SimpleUploadedFile(name="flag.svg", content=b"<svg></svg>", content_type="image/svg+xml")
    )

    @factory.post_generation
    def cities(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for city in extracted:
                self.cities.add(city)
        else:
            city = CityFactory.create()
            self.cities.add(city)


class GuessFactory(DjangoModelFactory):
    class Meta:
        model = "core.Guess"

    created_at = factory.Faker("date_time")
    is_correct = factory.fuzzy.FuzzyChoice([True, False])


class UserCountryScoreFactory(DjangoModelFactory):
    class Meta:
        model = "core.UserCountryScore"

    created_at = factory.Faker("date_time")
    user = factory.SubFactory(UserFactory)
    country = factory.SubFactory(CountryFactory)
    game_mode = factory.fuzzy.FuzzyChoice(["GUESS_COUNTRY_FROM_FLAG", "GUESS_CAPITAL_FROM_COUNTRY"])

    @factory.post_generation
    def user_guesses(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for guess in extracted:
                self.user_guesses.add(guess)
