import json

from app_saude.models import Observation
from app_saude.utils.concept import get_concept_by_code
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Seed interest areas and triggers for the SAÚDE application"

    def handle(self, *args, **options):
        self.stdout.write("Populando áreas de interesse")

        AOI_Triggers = [
            ("Hipertensão", "Você mediu sua pressão hoje?", "boolean"),
            ("Hipertensão", "Qual foi o valor?", "int"),
            ("Hipertensão", "Em que horário mediu sua pressão?", "text"),
            ("Hipertensão", "Teve sintomas como dor de cabeça, tontura ou mal-estar?", "boolean"),
            # ("Hipertensão", "Gostaria de compartilhar esta informação com profissionais do CAPS ou da UBS?"),
            ("Diabetes", "Você mediu sua glicemia hoje?", "boolean"),
            ("Diabetes", "Qual foi o valor?", "int"),
            ("Diabetes", "Em que horário mediu sua glicemia?", "text"),
            ("Diabetes", "Teve sintomas de hipo ou hiperglicemia?", "boolean"),
            # ("Diabetes", "Gostaria de compartilhar esta informação com profissionais do CAPS ou da UBS?"),
            ("Sono", "Que horas você dormiu e acordou?", "text"),
            ("Sono", "Dormiu bem esta noite?", "boolean"),
            ("Sono", "Acordou durante a noite?", "boolean"),
            ("Sono", "Quantas horas dormiu?", "int"),
            ("Meus Exames Clínicos", "Você realizou algum exame clínico recentemente?", "boolean"),
            ("Meus Exames Clínicos", "Qual exame foi realizado?", "text"),
            ("Meus Exames Clínicos", "Recebeu o resultado?", "boolean"),
            ("Meus Exames Clínicos", "Gostaria de discutir esse exame com alguém do CAPS ou da UBS?", "boolean"),
            ("Dores que estou sentindo", "Está sentindo alguma dor hoje?", "boolean"),
            ("Dores que estou sentindo", "Onde é a dor?", "text"),
            ("Dores que estou sentindo", "De 0 a 10, qual a intensidade da dor?", "scale"),
            ("Dores que estou sentindo", "Desde quando está com essa dor?", "text"),
            ("Dores que estou sentindo", "Gostaria de relatar isso para seu profissional de saúde?", "boolean"),
            ("Minha Saúde Mental", "Como você está se sentindo agora?", "text"),
            ("Minha Saúde Mental", "Teve momentos de ansiedade, tristeza ou irritação hoje?", "boolean"),
            ("Minha Saúde Mental", "Conseguiu se concentrar nas suas atividades?", "boolean"),
            # ("Minha Saúde Mental", "Gostaria de compartilhar como está se sentindo com sua equipe de cuidado?"),
            ("Medicação", "Você tomou sua medicação hoje?", "boolean"),
            ("Medicação", "Em que horário tomou?", "text"),
            ("Medicação", "Teve algum efeito colateral?", "boolean"),
            ("Medicação", "Gostaria de comunicar isso ao CAPS ou à UBS?", "boolean"),
            ("Alimentação", "Como foi sua alimentação hoje?", "text"),
            ("Alimentação", "Conseguiu fazer suas refeições principais?", "boolean"),
            ("Alimentação", "Teve algum enjoo, vômito ou falta de apetite?", "boolean"),
            ("Alimentação", "Bebeu bastante água hoje?", "boolean"),
            (
                "Uso de álcool ou outras substâncias",
                "Usou alguma substância hoje (álcool, cigarro, outras)?",
                "boolean",
            ),
            ("Uso de álcool ou outras substâncias", "Que horas foi o uso?", "text"),
            ("Uso de álcool ou outras substâncias", "Sentiu vontade de usar e conseguiu evitar?", "boolean"),
            ("Uso de álcool ou outras substâncias", "Gostaria de apoio para lidar com isso?", "boolean"),
            ("Humor e saúde emocional", "Como você está se sentindo neste momento?", "text"),
            ("Humor e saúde emocional", "Se sentiu sozinho(a) hoje?", "boolean"),
            ("Humor e saúde emocional", "Teve pensamentos difíceis de controlar?", "boolean"),
            ("Humor e saúde emocional", "Gostaria de conversar com alguém sobre isso?", "boolean"),
            ("Atividades do dia a dia", "Conseguiu tomar banho e se alimentar hoje?", "boolean"),
            ("Atividades do dia a dia", "Realizou alguma atividade em casa?", "boolean"),
            ("Atividades do dia a dia", "Saiu de casa hoje?", "boolean"),
            ("Atividades do dia a dia", "Teve dificuldade com alguma atividade cotidiana?", "boolean"),
            ("Atividades do dia a dia", "Gostaria de relatar isso para seu profissional de saúde?", "boolean"),
            ("Segurança e proteção social", "Se sentiu seguro(a) no lugar onde dormiu?", "boolean"),
            ("Segurança e proteção social", "Alguém te tratou mal ou te ameaçou hoje?", "boolean"),
            ("Segurança e proteção social", "Faltou algo essencial (comida, lugar para dormir)?", "boolean"),
            (
                "Segurança e proteção social",
                "Gostaria que um ACS ou profissional de saúde entrasse em contato com você?",
                "boolean",
            ),
            ("Rede de apoio e vínculos", "Conversou com alguém próximo hoje?", "boolean"),
            ("Rede de apoio e vínculos", "Participou de alguma atividade em grupo?", "boolean"),
            ("Rede de apoio e vínculos", "Teve vontade de encontrar alguém?", "boolean"),
            ("Rede de apoio e vínculos", "Gostaria de participar de atividades com outras pessoas?", "boolean"),
        ]

        interest_area_triggers = {}
        for interest_area, trigger_text, type in AOI_Triggers:
            if interest_area not in interest_area_triggers:
                interest_area_triggers[interest_area] = []

            trigger = {"name": trigger_text, "type": type}
            interest_area_triggers[interest_area].append(trigger)

        for interest_area, triggers in interest_area_triggers.items():
            interest_area_data = {
                "name": interest_area,
                "is_attention_point": False,
                "marked_by": [],
                "triggers": triggers,
            }

            Observation.objects.update_or_create(
                observation_concept_id=get_concept_by_code("INTEREST_AREA").concept_id,
                value_as_string=json.dumps(interest_area_data, ensure_ascii=False),
                defaults={"observation_date": timezone.now()},
            )

        self.stdout.write(self.style.SUCCESS("✔️  Interest areas and triggers seeded successfully."))
