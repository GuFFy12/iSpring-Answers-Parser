import requests
import re
import json
import base64
from bs4 import BeautifulSoup


def parse_answers(answers_unparsed, pic_uri):
    data = []
    for block in answers_unparsed["d"]["sl"]["g"]:
        for question_unparsed in block["S"]:

            question = ""
            answer = []
            answer_cleared = []

            for question_val in question_unparsed["D"]["d"]:
                if type(question_val) is dict:
                    for question_equation in question_unparsed["D"]["r"]:
                        if question_equation["id"] == question_val["id"]:
                            if "mathml" in question_equation:
                                question += " " + BeautifulSoup(question_equation["mathml"], "html.parser").get_text()
                            else:
                                question += " " + BeautifulSoup(question_equation["svg"], "html.parser").get_text()
                else:
                    question += " " + question_val

            if 'at' in question_unparsed:
                question += f" {pic_uri}/{question_unparsed['at']['i']['i'].split('//')[1]}"

            if question == "":
                question += f"Неизвестный вопрос:"

            question = " ".join(question.replace("\n", " ").strip().split())

            for answer_type in question_unparsed["C"].keys():
                answer_unparsed = question_unparsed["C"][answer_type]
                # Better solution - check answer type in question_unparsed
                if answer_type == "chs":
                    for possible_answer in answer_unparsed:
                        ans = ""
                        if "d" in possible_answer["t"]:
                            if "c" in possible_answer:
                                if possible_answer["c"]:
                                    for answer_val in possible_answer["t"]["d"]:
                                        if type(answer_val) is dict:
                                            for answer_equation in possible_answer["t"]["r"]:
                                                if answer_equation["id"] == answer_val["id"]:
                                                    if "mathml" in answer_equation:
                                                        ans += " " + BeautifulSoup(answer_equation["mathml"],
                                                                                   "html.parser").get_text()
                                                    else:
                                                        ans += " " + BeautifulSoup(answer_equation["svg"],
                                                                                   "html.parser").get_text()
                                        else:
                                            ans += " " + answer_val

                                    if "ia" in possible_answer:
                                        ans += f" {pic_uri}/{possible_answer['ia']['i'].split('//')[1]}"

                                    if ans == "":
                                        ans += "Неизвестный ответ"
                            else:
                                for answer_val in possible_answer["t"]["d"]:
                                    if type(answer_val) is dict:
                                        for answer_equation in possible_answer["t"]["r"]:
                                            if answer_equation["id"] == answer_val["id"]:
                                                ans += " " + BeautifulSoup(answer_equation["mathml"],
                                                                           "html.parser").get_text()
                                    else:
                                        ans += " " + answer_val

                                if "ia" in possible_answer:
                                    ans += f" {pic_uri}/{possible_answer['ia']['i'].split('//')[1]}"

                                if ans == "":
                                    ans += "Неизвестный ответ"
                        else:
                            ans += " " + possible_answer["t"]

                        if ans != "":
                            answer.append(ans)

                elif answer_type == "m":
                    for answer_val in answer_unparsed:
                        ansp = ""
                        ansr = ""

                        if len(answer_val["p"]["t"]["d"]) > 0:
                            ansp += answer_val["p"]["t"]["d"][0]

                        if len(answer_val["r"]["t"]["d"]) > 0:
                            ansr += answer_val["r"]["t"]["d"][0]

                        if len(answer_val["p"]["t"]["d"]) > 1 or len(answer_val["r"]["t"]["d"]) > 1:
                            print("y")

                        if "ia" in answer_val["p"]:
                            ansp += f" {pic_uri}/{answer_val['p']['ia']['i'].split('//')[1]}"
                        if "ia" in answer_val['r']:
                            ansr += f" {pic_uri}/{answer_val['r']['ia']['i'].split('//')[1]}"

                        if ansp == "":
                            ansp += "Неизвестный ответ"
                        if ansr == "":
                            ansr += "Неизвестный ответ"

                        answer.append(f'{ansp} - {ansr}')

                elif answer_type == "rt":
                    ans = ""
                    for answer_val in answer_unparsed["d"]:
                        if type(answer_val) is dict:
                            for answer_equation in answer_unparsed["r"]:
                                if answer_equation["id"] == answer_val["id"]:
                                    if "i" in answer_equation["data"]:
                                        ans += " " + answer_equation["data"]["v"][answer_equation["data"]["i"]]
                                    else:
                                        ans += " " + answer_equation["data"]["v"][0]
                        else:
                            ans += " " + answer_val

                    if ans != "":
                        answer.append(ans)

                elif answer_type == "d":
                    try:
                        for answer_val in answer_unparsed:
                            answer.append(f'{answer_val["o"]["s"]} - {answer_val["d"]["s"]}')
                    except:
                        pass

            for answerd in answer:
                answerd = " ".join(answerd.replace("\n", " ").strip().split())
                answer_cleared.append(answerd)

            question_obj = {}
            question_obj["question"] = question
            question_obj["answer"] = answer_cleared
            data.append(question_obj)

    return data


def get_answers(moodle_session, election_url):
    try:
        context_id_unparsed = re.findall(r'"contextid":\d{6}', requests.get(election_url, cookies={"MoodleSession": moodle_session}).text)
    except:
        print(election_url)
        return
    if len(context_id_unparsed) == 0:
        return

    test_url = f"https://sdo.ugatu.su/pluginfile.php/{context_id_unparsed[0].split(':')[1]}/mod_scorm/content/1/res"

    test_request = requests.get(f"{test_url}/index.html", cookies={"MoodleSession": moodle_session})

    test_num = 1
    test_object = {}
    if "var data =" in test_request.text:
        test_name = f"Тест {test_num}"
        picture_url = f"{test_url}/data"
        test_object[test_name] = parse_answers(json.loads(base64.b64decode(test_request.text.split('var data = "')[1].split('";')[0]).decode('utf-8')), picture_url)

        return test_object
    else:
        while True:
            test_request = requests.get(f"{test_url}/data/quiz{test_num}.js", cookies={"MoodleSession": moodle_session})
            if test_request.status_code == 404:
                break
            else:
                test_name = f"Тест {test_num}"
                picture_url = f"{test_url}/data/quiz{test_num}"
                test_object[test_name] = parse_answers(json.loads(base64.b64decode(test_request.text.split('var quizInfo = "')[1].split('";')[0]).decode('utf-8')), picture_url)

            test_num += 1

        return test_object


def find_courses(moodle_session):
    courses_unparsed = requests.get("https://sdo.ugatu.su", cookies={"MoodleSession": moodle_session}).text
    return list(set(re.findall(r"https://sdo\.ugatu\.su/course/view\.php\?id=\d{4}", courses_unparsed)))


def generate_answers(moodle_session, courses_url_checked):
    courses_url = find_courses(moodle_session)

    answers_object = {}
    for course_url in courses_url:
        if course_url in courses_url_checked:
            continue

        elections_request = requests.get(course_url, cookies={"MoodleSession": moodle_session}).text
        elections_soup = BeautifulSoup(elections_request, 'html.parser')

        section_id = 0
        while True:
            section = elections_soup.find(id=f"section-{section_id}")
            if section is None:
                break

            course_title = " ".join(elections_soup.title.string.replace("Курс: ", "").strip().split())
            section_name = " ".join(section.find(class_="sectionname").string.strip().split())

            for election_object in section.find_all(class_="aalink"):
                election_name = " ".join(str(election_object.find(class_="instancename")).split('>')[1].split('<')[0].strip().split())

                answers_parsed = get_answers(moodle_session, election_object["href"])

                if answers_parsed:
                    courses_url_checked.append(course_url)

                    if course_title not in answers_object:
                        answers_object[course_title] = {}
                    if section_name not in answers_object[course_title]:
                        answers_object[course_title][section_name] = {}

                    answers_object[course_title][section_name][election_name] = answers_parsed

            section_id += 1

    return {"answers_object": answers_object, "courses_url_checked": list(set(courses_url_checked))}


answers = json.load(open("answers.json"))

new_answers = generate_answers("UR MOODLE TOKEN", json.load(open("courses_url_checked.json")))
for course in new_answers["answers_object"]:
    answers[course].update(new_answers["answers_object"][course])

with open("courses_url_checked.json", "w") as file:
    json.dump(new_answers["courses_url_checked"], file, ensure_ascii=False, indent=4)

with open('answers.json', 'w') as file:
    json.dump(answers, file, ensure_ascii=False, indent=4)
