from django.core.management.base import BaseCommand

from core.models import Department


class Command(BaseCommand):
    help = "Import French departments data"

    def handle(self, *args, **options):
        departments_data = [
            {"number": "01", "name": "Ain", "region": "Auvergne-Rhône-Alpes", "prefecture": "Bourg-en-Bresse"},
            {"number": "02", "name": "Aisne", "region": "Hauts-de-France", "prefecture": "Laon"},
            {"number": "03", "name": "Allier", "region": "Auvergne-Rhône-Alpes", "prefecture": "Moulins"},
            {"number": "04", "name": "Alpes-de-Haute-Provence", "region": "Provence-Alpes-Côte d'Azur", "prefecture": "Digne-les-Bains"},
            {"number": "05", "name": "Hautes-Alpes", "region": "Provence-Alpes-Côte d'Azur", "prefecture": "Gap"},
            {"number": "06", "name": "Alpes-Maritimes", "region": "Provence-Alpes-Côte d'Azur", "prefecture": "Nice"},
            {"number": "07", "name": "Ardèche", "region": "Auvergne-Rhône-Alpes", "prefecture": "Privas"},
            {"number": "08", "name": "Ardennes", "region": "Grand Est", "prefecture": "Charleville-Mézières"},
            {"number": "09", "name": "Ariège", "region": "Occitanie", "prefecture": "Foix"},
            {"number": "10", "name": "Aube", "region": "Grand Est", "prefecture": "Troyes"},
            {"number": "11", "name": "Aude", "region": "Occitanie", "prefecture": "Carcassonne"},
            {"number": "12", "name": "Aveyron", "region": "Occitanie", "prefecture": "Rodez"},
            {"number": "13", "name": "Bouches-du-Rhône", "region": "Provence-Alpes-Côte d'Azur", "prefecture": "Marseille"},
            {"number": "14", "name": "Calvados", "region": "Normandie", "prefecture": "Caen"},
            {"number": "15", "name": "Cantal", "region": "Auvergne-Rhône-Alpes", "prefecture": "Aurillac"},
            {"number": "16", "name": "Charente", "region": "Nouvelle-Aquitaine", "prefecture": "Angoulême"},
            {"number": "17", "name": "Charente-Maritime", "region": "Nouvelle-Aquitaine", "prefecture": "La Rochelle"},
            {"number": "18", "name": "Cher", "region": "Centre-Val de Loire", "prefecture": "Bourges"},
            {"number": "19", "name": "Corrèze", "region": "Nouvelle-Aquitaine", "prefecture": "Tulle"},
            {"number": "2A", "name": "Corse-du-Sud", "region": "Corse", "prefecture": "Ajaccio"},
            {"number": "2B", "name": "Haute-Corse", "region": "Corse", "prefecture": "Bastia"},
            {"number": "21", "name": "Côte-d'Or", "region": "Bourgogne-Franche-Comté", "prefecture": "Dijon"},
            {"number": "22", "name": "Côtes-d'Armor", "region": "Bretagne", "prefecture": "Saint-Brieuc"},
            {"number": "23", "name": "Creuse", "region": "Nouvelle-Aquitaine", "prefecture": "Guéret"},
            {"number": "24", "name": "Dordogne", "region": "Nouvelle-Aquitaine", "prefecture": "Périgueux"},
            {"number": "25", "name": "Doubs", "region": "Bourgogne-Franche-Comté", "prefecture": "Besançon"},
            {"number": "26", "name": "Drôme", "region": "Auvergne-Rhône-Alpes", "prefecture": "Valence"},
            {"number": "27", "name": "Eure", "region": "Normandie", "prefecture": "Évreux"},
            {"number": "28", "name": "Eure-et-Loir", "region": "Centre-Val de Loire", "prefecture": "Chartres"},
            {"number": "29", "name": "Finistère", "region": "Bretagne", "prefecture": "Quimper"},
            {"number": "30", "name": "Gard", "region": "Occitanie", "prefecture": "Nîmes"},
            {"number": "31", "name": "Haute-Garonne", "region": "Occitanie", "prefecture": "Toulouse"},
            {"number": "32", "name": "Gers", "region": "Occitanie", "prefecture": "Auch"},
            {"number": "33", "name": "Gironde", "region": "Nouvelle-Aquitaine", "prefecture": "Bordeaux"},
            {"number": "34", "name": "Hérault", "region": "Occitanie", "prefecture": "Montpellier"},
            {"number": "35", "name": "Ille-et-Vilaine", "region": "Bretagne", "prefecture": "Rennes"},
            {"number": "36", "name": "Indre", "region": "Centre-Val de Loire", "prefecture": "Châteauroux"},
            {"number": "37", "name": "Indre-et-Loire", "region": "Centre-Val de Loire", "prefecture": "Tours"},
            {"number": "38", "name": "Isère", "region": "Auvergne-Rhône-Alpes", "prefecture": "Grenoble"},
            {"number": "39", "name": "Jura", "region": "Bourgogne-Franche-Comté", "prefecture": "Lons-le-Saunier"},
            {"number": "40", "name": "Landes", "region": "Nouvelle-Aquitaine", "prefecture": "Mont-de-Marsan"},
            {"number": "41", "name": "Loir-et-Cher", "region": "Centre-Val de Loire", "prefecture": "Blois"},
            {"number": "42", "name": "Loire", "region": "Auvergne-Rhône-Alpes", "prefecture": "Saint-Étienne"},
            {"number": "43", "name": "Haute-Loire", "region": "Auvergne-Rhône-Alpes", "prefecture": "Le Puy-en-Velay"},
            {"number": "44", "name": "Loire-Atlantique", "region": "Pays de la Loire", "prefecture": "Nantes"},
            {"number": "45", "name": "Loiret", "region": "Centre-Val de Loire", "prefecture": "Orléans"},
            {"number": "46", "name": "Lot", "region": "Occitanie", "prefecture": "Cahors"},
            {"number": "47", "name": "Lot-et-Garonne", "region": "Nouvelle-Aquitaine", "prefecture": "Agen"},
            {"number": "48", "name": "Lozère", "region": "Occitanie", "prefecture": "Mende"},
            {"number": "49", "name": "Maine-et-Loire", "region": "Pays de la Loire", "prefecture": "Angers"},
            {"number": "50", "name": "Manche", "region": "Normandie", "prefecture": "Saint-Lô"},
            {"number": "51", "name": "Marne", "region": "Grand Est", "prefecture": "Châlons-en-Champagne"},
            {"number": "52", "name": "Haute-Marne", "region": "Grand Est", "prefecture": "Chaumont"},
            {"number": "53", "name": "Mayenne", "region": "Pays de la Loire", "prefecture": "Laval"},
            {"number": "54", "name": "Meurthe-et-Moselle", "region": "Grand Est", "prefecture": "Nancy"},
            {"number": "55", "name": "Meuse", "region": "Grand Est", "prefecture": "Bar-le-Duc"},
            {"number": "56", "name": "Morbihan", "region": "Bretagne", "prefecture": "Vannes"},
            {"number": "57", "name": "Moselle", "region": "Grand Est", "prefecture": "Metz"},
            {"number": "58", "name": "Nièvre", "region": "Bourgogne-Franche-Comté", "prefecture": "Nevers"},
            {"number": "59", "name": "Nord", "region": "Hauts-de-France", "prefecture": "Lille"},
            {"number": "60", "name": "Oise", "region": "Hauts-de-France", "prefecture": "Beauvais"},
            {"number": "61", "name": "Orne", "region": "Normandie", "prefecture": "Alençon"},
            {"number": "62", "name": "Pas-de-Calais", "region": "Hauts-de-France", "prefecture": "Arras"},
            {"number": "63", "name": "Puy-de-Dôme", "region": "Auvergne-Rhône-Alpes", "prefecture": "Clermont-Ferrand"},
            {"number": "64", "name": "Pyrénées-Atlantiques", "region": "Nouvelle-Aquitaine", "prefecture": "Pau"},
            {"number": "65", "name": "Hautes-Pyrénées", "region": "Occitanie", "prefecture": "Tarbes"},
            {"number": "66", "name": "Pyrénées-Orientales", "region": "Occitanie", "prefecture": "Perpignan"},
            {"number": "67", "name": "Bas-Rhin", "region": "Grand Est", "prefecture": "Strasbourg"},
            {"number": "68", "name": "Haut-Rhin", "region": "Grand Est", "prefecture": "Colmar"},
            {"number": "69", "name": "Rhône", "region": "Auvergne-Rhône-Alpes", "prefecture": "Lyon"},
            {"number": "70", "name": "Haute-Saône", "region": "Bourgogne-Franche-Comté", "prefecture": "Vesoul"},
            {"number": "71", "name": "Saône-et-Loire", "region": "Bourgogne-Franche-Comté", "prefecture": "Mâcon"},
            {"number": "72", "name": "Sarthe", "region": "Pays de la Loire", "prefecture": "Le Mans"},
            {"number": "73", "name": "Savoie", "region": "Auvergne-Rhône-Alpes", "prefecture": "Chambéry"},
            {"number": "74", "name": "Haute-Savoie", "region": "Auvergne-Rhône-Alpes", "prefecture": "Annecy"},
            {"number": "75", "name": "Paris", "region": "Île-de-France", "prefecture": "Paris"},
            {"number": "76", "name": "Seine-Maritime", "region": "Normandie", "prefecture": "Rouen"},
            {"number": "77", "name": "Seine-et-Marne", "region": "Île-de-France", "prefecture": "Melun"},
            {"number": "78", "name": "Yvelines", "region": "Île-de-France", "prefecture": "Versailles"},
            {"number": "79", "name": "Deux-Sèvres", "region": "Nouvelle-Aquitaine", "prefecture": "Niort"},
            {"number": "80", "name": "Somme", "region": "Hauts-de-France", "prefecture": "Amiens"},
            {"number": "81", "name": "Tarn", "region": "Occitanie", "prefecture": "Albi"},
            {"number": "82", "name": "Tarn-et-Garonne", "region": "Occitanie", "prefecture": "Montauban"},
            {"number": "83", "name": "Var", "region": "Provence-Alpes-Côte d'Azur", "prefecture": "Toulon"},
            {"number": "84", "name": "Vaucluse", "region": "Provence-Alpes-Côte d'Azur", "prefecture": "Avignon"},
            {"number": "85", "name": "Vendée", "region": "Pays de la Loire", "prefecture": "La Roche-sur-Yon"},
            {"number": "86", "name": "Vienne", "region": "Nouvelle-Aquitaine", "prefecture": "Poitiers"},
            {"number": "87", "name": "Haute-Vienne", "region": "Nouvelle-Aquitaine", "prefecture": "Limoges"},
            {"number": "88", "name": "Vosges", "region": "Grand Est", "prefecture": "Épinal"},
            {"number": "89", "name": "Yonne", "region": "Bourgogne-Franche-Comté", "prefecture": "Auxerre"},
            {"number": "90", "name": "Territoire de Belfort", "region": "Bourgogne-Franche-Comté", "prefecture": "Belfort"},
            {"number": "91", "name": "Essonne", "region": "Île-de-France", "prefecture": "Évry-Courcouronnes"},
            {"number": "92", "name": "Hauts-de-Seine", "region": "Île-de-France", "prefecture": "Nanterre"},
            {"number": "93", "name": "Seine-Saint-Denis", "region": "Île-de-France", "prefecture": "Bobigny"},
            {"number": "94", "name": "Val-de-Marne", "region": "Île-de-France", "prefecture": "Créteil"},
            {"number": "95", "name": "Val-d'Oise", "region": "Île-de-France", "prefecture": "Cergy"},
            {"number": "971", "name": "Guadeloupe", "region": "Guadeloupe", "prefecture": "Basse-Terre"},
            {"number": "972", "name": "Martinique", "region": "Martinique", "prefecture": "Fort-de-France"},
            {"number": "973", "name": "Guyane", "region": "Guyane", "prefecture": "Cayenne"},
            {"number": "974", "name": "La Réunion", "region": "La Réunion", "prefecture": "Saint-Denis"},
            {"number": "976", "name": "Mayotte", "region": "Mayotte", "prefecture": "Mamoudzou"},
        ]

        created_count = 0
        updated_count = 0

        for dept_data in departments_data:
            department, created = Department.objects.get_or_create(
                number=dept_data["number"],
                defaults=dept_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(f"Created: {department}")
            else:
                # Update existing department
                for key, value in dept_data.items():
                    if key != "number":  # Don't update the unique key
                        setattr(department, key, value)
                department.save()
                updated_count += 1
                self.stdout.write(f"Updated: {department}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed. Created: {created_count}, Updated: {updated_count}"
            )
        )