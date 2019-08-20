''' This file contains the code for training and testing the model. Adam optimizer is used for training with a
learning rate of 0.001 and a batch size of 128. Training is done for 256 epochs with early stopping
if validation loss doesn't decrease within last 20 epochs. Weights are initialized  using Xavier Initialization
except for word embeddings. Dropout and L2 are used as regularization methos on sentence encodings and answer module.'''

import os
import torch
import numpy as np
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as f
from torch.autograd import Variable
from torch.utils.data import DataLoader
from modelDMN import DMN
from dmn_loader import BabiDataSet, pad_collate


if __name__ == '__main__':
    for itr in range(10):
        for task_id in range(1,21):
            dataset= BabiDataSet(task_id)
            vocab_size= len(dataset.QA.VOCAB)
            hidden_size= 100

            model = DMN(hidden_size, vocab_size, num_pass= 3)   ##vocab_size denotes the size of word embedding used
            model = model.cuda()

            early_stop_count= 0
            early_stop_flag= False
            best_acc= 0
            optim= torch.optim.Adam(model.parameters())

            for epoch in range(256):
                dataset.set_mode('train')
                train_load= DataLoader(dataset, batch_size=100, shuffle= True, collate_fn= pad_collate)  ### Loading the babi dataset

                model.train()                                                       ### training the network
                if not early_stop_flag:
                    total_acc=0
                    count= 0
                    for batch_id, data in enumerate(train_load):
                        optim.zero_grad()
                        context, questions, answers = data
                        batch_size= context.size()[0]
                        context= Variable(context.long().cuda())                           ## context.size() = (batch_size, num_sentences, embedding_length) embedding_length = hidden_size
                        questions= Variable(questions.long().cuda())                       ## questions.size() = (batch_size, num_tokens)
                        answers= Variable(answers.long().cuda())

                        total_loss, acc = model.loss(context,questions,answers)      ## Loss is calculated and gradients are backpropagated through the layers.
                        total_loss.backward()
                        total_acc += acc*batch_size
                        count += batch_size

                        if batch_id %20 == 0:
                            print('Training Error')
                            print (f'[Task {task_id}, Epoch {epoch}] [Training] total_loss : {total_loss.data.item(): {10}.{8}}, acc : {total_acc / count: {5}.{4}}, batch_id : {batch_id}')
                        optim.step()

                    '''Validation part'''


                    dataset.set_mode('valid')
                    valid_load = DataLoader(dataset, batch_size=100, shuffle=False, collate_fn=pad_collate)    ## Loading the validation data

                    model.eval()
                    total_acc = 0
                    count = 0
                    for batch_idx,data in enumerate(valid_load):
                        context, questions, answers = data
                        batch_size = context.size()[0]
                        context = Variable(context.long().cuda())
                        questions = Variable(questions.long().cuda())
                        answers = Variable(answers.long().cuda())

                        _, acc = model.loss(context,questions,answers)
                        total_acc += acc*batch_size
                        count += batch_size

                    total_acc = total_acc / count

                    if total_acc > best_acc:
                        best_acc = total_acc
                        best_state = model.state_dict()
                        early_stop_count = 0
                    else:
                        early_stop_count += 1
                        if early_stop_count > 20: # If the accuracy doesn't improve even after 20 epochs thenuse early stopping.
                            early_Stop_flag = True

                    print (f'[Run {itr}, Task {task_id}, Epoch {epoch}] [Validate] Accuracy : {total_acc: {5}.{4}}')

                    with open('log.txt', 'a') as fp:
                        fp.write(f'[Run {itr}, Task {task_id}, Epoch {epoch}] [Validate] Accuracy : {total_acc: {5}.{4}}' + '\n')
                    if total_acc == 1.0:
                        break
                else:
                    print(f'[Run {itr}, Task {task_id}] Early Stopping at Epoch {epoch}, Valid Accuracy : {best_acc: {5}.{4}}')


            dataset.set_mode('test')
            test_load= DataLoader(dataset, batch_size=100, shuffle= False, collate_fn= pad_collate)

            test_acc = 0
            count = 0

            for batch_id, data in enumerate(test_load):
                    context, questions, answers = data
                    batch_size = context.size()[0]
                    context = Variable(context.long().cuda())
                    questions = Variable(questions.long().cuda())
                    answers = Variable(answers.long().cuda())

                    model.load_state_dict(best_state) # Loading the best model
                    _, acc = model.loss(context, questions, answers)

                    test_acc += acc* batch_size
                    count += batch_size
                    print (f'[Run {itr}, Task {task_id}, Epoch {epoch}] [Test] Accuracy : {test_acc / count: {5}.{4}}')



                    os.makedirs('models',exist_ok=True)
                    with open(f'models/task{task_id}_epoch{epoch}_run{itr}_acc{test_acc/count}.pth', 'wb') as fp:
                        torch.save(model.state_dict(), fp)
                    with open('log.txt', 'a') as fp:
                        fp.write(f'[Run {itr}, Task {task_id}, Epoch {epoch}] [Test] Accuracy : {total_acc: {5}.{4}}' + '\n')
