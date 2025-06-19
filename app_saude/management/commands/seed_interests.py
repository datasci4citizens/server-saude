import json

from django.core.management.base import BaseCommand
from django.utils import timezone

from app_saude.models import Observation


class Command(BaseCommand):
    help = "Seed interest areas and triggers for the SAÚDE application"

    def handle(self, *args, **options):
        self.stdout.write("Populando áreas de interesse")

        AOI_Triggers = [
            ("Hipertensão", "Você mediu sua pressão hoje?"),
            ("Hipertensão", "Qual foi o valor?"),
            ("Hipertensão", "Em que horário mediu sua pressão?"),
            ("Hipertensão", "Teve sintomas como dor de cabeça, tontura ou mal-estar?"),
            # ("Hipertensão", "Gostaria de compartilhar esta informação com profissionais do CAPS ou da UBS?"),
            ("Diabetes", "Você mediu sua glicemia hoje?"),
            ("Diabetes", "Qual foi o valor?"),
            ("Diabetes", "Em que horário mediu sua glicemia?"),
            ("Diabetes", "Teve sintomas de hipo ou hiperglicemia?"),
            # ("Diabetes", "Gostaria de compartilhar esta informação com profissionais do CAPS ou da UBS?"),
            ("Sono", "Que horas você dormiu e acordou?"),
            ("Sono", "Dormiu bem esta noite?"),
            ("Sono", "Acordou durante a noite?"),
            ("Sono", "Quantas horas dormiu?"),
            ("Meus Exames Clínicos", "Você realizou algum exame clínico recentemente?"),
            ("Meus Exames Clínicos", "Qual exame foi realizado?"),
            ("Meus Exames Clínicos", "Recebeu o resultado?"),
            ("Meus Exames Clínicos", "Gostaria de discutir esse exame com alguém do CAPS ou da UBS?"),
            ("Dores que estou sentindo", "Está sentindo alguma dor hoje?"),
            ("Dores que estou sentindo", "Onde é a dor?"),
            ("Dores que estou sentindo", "De 0 a 10, qual a intensidade da dor?"),
            ("Dores que estou sentindo", "Desde quando está com essa dor?"),
            ("Dores que estou sentindo", "Gostaria de relatar isso para seu profissional de saúde?"),
            ("Minha Saúde Mental", "Como você está se sentindo agora?"),
            ("Minha Saúde Mental", "Teve momentos de ansiedade, tristeza ou irritação hoje?"),
            ("Minha Saúde Mental", "Conseguiu se concentrar nas suas atividades?"),
            # ("Minha Saúde Mental", "Gostaria de compartilhar como está se sentindo com sua equipe de cuidado?"),
            ("Medicação", "Você tomou sua medicação hoje?"),
            ("Medicação", "Em que horário tomou?"),
            ("Medicação", "Teve algum efeito colateral?"),
            ("Medicação", "Gostaria de comunicar isso ao CAPS ou à UBS?"),
            ("Alimentação", "Como foi sua alimentação hoje?"),
            ("Alimentação", "Conseguiu fazer suas refeições principais?"),
            ("Alimentação", "Teve algum enjoo, vômito ou falta de apetite?"),
            ("Alimentação", "Bebeu bastante água hoje?"),
            ("Uso de álcool ou outras substâncias", "Usou alguma substância hoje (álcool, cigarro, outras)?"),
            ("Uso de álcool ou outras substâncias", "Que horas foi o uso?"),
            ("Uso de álcool ou outras substâncias", "Sentiu vontade de usar e conseguiu evitar?"),
            ("Uso de álcool ou outras substâncias", "Gostaria de apoio para lidar com isso?"),
            ("Humor e saúde emocional", "Como você está se sentindo neste momento?"),
            ("Humor e saúde emocional", "Se sentiu sozinho(a) hoje?"),
            ("Humor e saúde emocional", "Teve pensamentos difíceis de controlar?"),
            ("Humor e saúde emocional", "Gostaria de conversar com alguém sobre isso?"),
            ("Atividades do dia a dia", "Conseguiu tomar banho e se alimentar hoje?"),
            ("Atividades do dia a dia", "Realizou alguma atividade em casa?"),
            ("Atividades do dia a dia", "Saiu de casa hoje?"),
            ("Atividades do dia a dia", "Teve dificuldade com alguma atividade cotidiana?"),
            ("Segurança e proteção social", "Se sentiu seguro(a) no lugar onde dormiu?"),
            ("Segurança e proteção social", "Alguém te tratou mal ou te ameaçou hoje?"),
            ("Segurança e proteção social", "Faltou algo essencial (comida, lugar para dormir)?"),
            (
                "Segurança e proteção social",
                "Gostaria que um ACS ou profissional de saúde entrasse em contato com você?",
            ),
            ("Rede de apoio e vínculos", "Conversou com alguém próximo hoje?"),
            ("Rede de apoio e vínculos", "Participou de alguma atividade em grupo?"),
            ("Rede de apoio e vínculos", "Teve vontade de encontrar alguém?"),
            ("Rede de apoio e vínculos", "Gostaria de participar de atividades com outras pessoas?"),
        ]

        interest_area_triggers = {}
        for interest_area, trigger_text in AOI_Triggers:
            if interest_area not in interest_area_triggers:
                interest_area_triggers[interest_area] = []

            trigger = {"name": trigger_text, "type": "boolean"}
            interest_area_triggers[interest_area].append(trigger)

        for interest_area, triggers in interest_area_triggers.items():
            interest_area_data = {
                "name": interest_area,
                "is_attention_point": False,
                "marked_by": [],
                "triggers": triggers,
            }

            Observation.objects.update_or_create(
                observation_concept_id=2000000200,  # Interest Area concept ID
                value_as_string=json.dumps(interest_area_data, ensure_ascii=False),
                defaults={"observation_date": timezone.now()},
            )

        self.stdout.write(self.style.SUCCESS("Áreas de Interesse populadas com sucesso."))
