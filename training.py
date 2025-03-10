import torch
from torch.utils.data import DataLoader, TensorDataset
import torch.optim as optim
import os

from help_func import self_feeding, enc_self_feeding
from loss_func import total_loss
from nn_structure import AUTOENCODER

def get_model_path(i):
    path1 = f"/home/trarity/master/koopman_control/data/Autoencoder_model_params{i}.pth"
    path2 = f"C:/Users/jokin/Desktop/Uni/Aalborg/Master/Masters_Thesis/Path/Autoencoder_model_params{i}.pth"
    path3 = f"/content/drive/My Drive/Colab Notebooks/Autoencoder_model_params{i}.pth"
    path4 = f"/content/drive/MyDrive/Colab Notebooks/Autoencoder_model_params{i}.pth"
    if os.path.exists(path1):
        return path1
    elif os.path.exists(path2):
        return path2
    elif os.path.exists(path3):
        return path3
    else:
        return path4

def trainingfcn(eps, lr, batch_size, S_p, T, alpha, Num_meas, Num_inputs, Num_x_Obsv, Num_x_Neurons, Num_u_Obsv, Num_u_Neurons, Num_hidden_x_encoder, Num_hidden_x_decoder, Num_hidden_u_encoder, Num_hidden_u_decoder, train_tensor, test_tensor, M):

  train_dataset = TensorDataset(train_tensor)
  train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

  test_dataset = TensorDataset(test_tensor)
  test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=True)

  Model_path = []
  Models_loss_list = []
  Test_loss_list = []
  Running_Losses_Array = []
  c_m = 0

  Model_path = [get_model_path(i) for i in range(M)]

  for model_path_i in Model_path:
      training_attempt = 0
      while True:  # Re-run the training loop until no NaN is encountered
          training_attempt += 1
          print(f"\nStarting training attempt #{training_attempt} for model {model_path_i}")

          # Instantiate the model and optimizer afresh
          model = AUTOENCODER(Num_meas, Num_inputs, Num_x_Obsv, Num_x_Neurons, Num_u_Obsv, Num_u_Neurons, Num_hidden_x_encoder, Num_hidden_x_decoder, Num_hidden_u_encoder, Num_hidden_u_decoder)
          optimizer = optim.Adam(model.parameters(), lr=lr)
          loss_list = []
          running_loss_list = []
          nan_found = False  # Flag to detect NaNs

          for e in range(eps):
              running_loss = 0.0
              for (batch_x,) in train_loader:
                  optimizer.zero_grad()
                  loss = total_loss(alpha, batch_x, Num_meas, Num_x_Obsv, T, S_p, model)

                  # Check if loss is NaN; if so, break out of loops
                  if torch.isnan(loss):
                      nan_found = True
                      print(f"NaN detected at epoch {e+1}. Restarting training attempt.")
                      break

                  loss.backward()
                  optimizer.step()
                  running_loss += loss.item()
                  torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=2.0)

              if nan_found:
                  break

              avg_loss = running_loss / len(train_loader)
              loss_list.append(avg_loss)
              running_loss_list.append(running_loss)
              print(f'Epoch {e+1}, Avg Loss: {avg_loss:.10f}, Running loss: {running_loss:.3e}')
              current_lr = optimizer.param_groups[0]['lr']
              print(f'Current learning rate: {current_lr:.8f}')

              # Save the model parameters at the end of each epoch
              torch.save(model.state_dict(), model_path_i)

          # If no NaN was found during this training attempt, we exit the loop
          if not nan_found:
              break
          else:
              print("Restarting training loop due to NaN encountered.\n")

      Models_loss_list.append(running_loss)
      Running_Losses_Array.append(running_loss_list)
      torch.save(model.state_dict(), model_path_i)

      for (batch_x,) in test_loader:
        [traj_prediction, loss] = enc_self_feeding(model, batch_x, Num_meas)
        running_loss += loss.item()

      avg_loss = running_loss / len(test_loader)
      print(f'Test Data w/Model {c_m + 1}, Avg Loss: {avg_loss:.10f}, Running loss: {running_loss:.3e}')
      Test_loss_list.append(running_loss)
      c_m += 1

  # Find the best of the models
  Lowest_loss = min(Models_loss_list)
  Lowest_test_loss = min(Test_loss_list)

  Lowest_loss_index = Models_loss_list.index(Lowest_loss)
  print(f"The best model has a running loss of {Lowest_loss} and is model nr. {Lowest_loss_index + 1}")

  Lowest_test_loss_index = Test_loss_list.index(Lowest_test_loss)
  print(f"The best model has a test running loss of {Lowest_test_loss} and is model nr. {Lowest_test_loss_index + 1}")

  Best_Model = Model_path[Lowest_test_loss_index]

  return Lowest_loss, Lowest_test_loss, Best_Model
