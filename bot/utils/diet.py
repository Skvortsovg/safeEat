# *-* coding: utf-8 *-*


# sex 0 for female and 1 fro male
def get_daily_rate(age, weight, height, goal_coeff, lifestyle_coeff, sex):
    """ calculate daily norm.
        http://pohudejkina.ru/raschet-sutochnoj-normy-kalorij-i-bzhu
        Intake of calories calculated by the Harris-Benedict equation.
        INPUT DATA: age(in years),
                    weight(kilograms),
                    height(centimeters),
                    goal_coeff (0.8, 1 or 1.2)
                    lifestyle_coeff (1.2, 1.375, 1.55, 1.725, 1.9),
                    sex (0 for women and 1 for men),
                    age (in years)
        OUTPUT: dict with calories, proteins, fats and carbohydrates """
    age = int(age)
    weight = int(weight)
    height = int(height)
    goal_coeff = int(goal_coeff)
    lifestyle_coeff = int(lifestyle_coeff)
    sex = int(sex)
    female_c = [447.593, 9.247, 3.098, 4.330]
    male_c = [88.362, 13.397, 4.799, 5.677]
    args = female_c if sex == 0 else male_c
    calories = (args[0] + args[1] * weight + args[2] * height - args[3] * age) * goal_coeff * lifestyle_coeff
    norm = {'calories': int(calories),
           'proteins': int(calories * 0.4 / 4),
           'fats': int(calories * 0.2 / 9),
           'carbohydrates': int(calories * 0.4 / 4)}
    return norm



