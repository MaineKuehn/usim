from typing import List
import random

from usim import run, time, each, until, Flag, Lock
from usim.basics import Queue


customer_names = [
        'Alfred', 'Betty', 'Charlie', 'Dorothee', 'Emilio', 'Fiona', 'George', 'Harriet', 'Isaac', 'Janet', 'Kurt',
        'Leonore', 'Mathew', 'Nicky', 'Oswald', 'Priscilla', 'Quentin', 'Rachel', 'Simon', 'Trina', 'Ulysses',
        'Veronica', 'Walter', 'Xenia', 'Yves', 'Zoe'
    ]


def clock() -> str:
    now = time.now
    return '%02d:%02d:%02d' % (now // 60 // 60, now // 60 % 60, now % 60)


def narrate(*message):
    print('<%s ' % clock(), *message, '>')


def say(name: str, *message):
    print('[%s] % 20s:' % (clock(), name), *message)


async def coffee_house(opens=8, closes=16, tables=2):
    # set_trace()
    await (time == opens * 60 * 60)
    seats = [Lock() for _ in range(tables * 4)]
    orders = Queue()
    narrate('Coffee shop opens with', len(seats), 'seats')
    async with until(time == closes * 60 * 60) as while_open:
        for waiter in ('Annabelle', 'Bonita', 'Charleen', 'Drusilla'):
            while_open.do(service(name=waiter, orders=orders))
        async for _ in each(delay=20):
            while random.random() > 0.95:
                while_open.do(customer(random.choice(customer_names), seats=seats, orders=orders))
    narrate('Coffee shop closes')


async def service(name: str, orders: Queue):
    say(name, 'What a lovely day to serve!')
    async for _ in each(delay=60):
        customer, order = await orders
        say(name, 'Hello', customer, 'how may I serve you?')
        await order(name)


async def customer(name: str, seats: List[Lock], orders: Queue):
    free_seats = [seat for seat in seats if seat.available]
    if not free_seats:
        say(name, 'Outrageous!', 'Not even a single free seat!')
        return
    async with free_seats[0]:
        for food in (('coffee', 'cake'), ('tee',)):
            served, order = make_order(name, *food)
            await orders.put((name, order))
            await served
            await (time + len(food) * 20 * (1 + random.random()))


def make_order(customer: str, *orders: str):
    served = Flag()

    async def serve_order(waiter: str):
        say(customer, "I'll take", ', '.join(orders), ", please!")
        say(waiter, 'Sure, just a sec...')
        await (time + len(orders) * 20 * (1 + random.random()))
        say(waiter, 'Here you are,', customer, '! Your', ', '.join(orders), '!')
        await served.set()
    return served, serve_order


run(coffee_house())
