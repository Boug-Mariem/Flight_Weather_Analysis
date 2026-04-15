from transformation.delay_predection import predict_delay

if __name__ == "__main__":
        print("*****************************Predction***************************")
        print("*** avec Airports seulement")
        predict_delay("LAX", airline=None)
        print("*** avec Airports et airline")
        predict_delay("LAX", "Skywest Airlines Inc.")