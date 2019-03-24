from usim import time, run, until


async def car(end: float):
    async with until(time == end):
        while True:
            print('Start parking at %d' % time.now)
            parking_duration = 5
            await (time + parking_duration)

            print('Start driving at %d' % time.now)
            trip_duration = 2
            await (time + trip_duration)


def perform(end: float = 1000000):
    run(car(end))


if __name__ == '__main__':
    perform()
