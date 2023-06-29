import json
if __name__=="__main__":
	output = open("output.txt",'w+')
	dictOrder = {}
	i=0
	with open("./dbinsectidentification/DBinsectidentificationJSON23.txt",'r') as f:
		for line in f:
			i+=1
			try:
				print(json.loads(line)['Descriptors'].replace(";","\n"))
				dictOrder[json.loads(line)['Descriptors']] = json.loads(line)['Descriptors']
			except KeyError:
				print("errore riga "+str(i))
		for val in dictOrder.values():
			output.write(val)

	output.flush()
	output.close()
