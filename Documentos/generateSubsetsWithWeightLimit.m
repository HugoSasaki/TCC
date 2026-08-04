function [valid_subsets_matrix, valid_sums_vector] = generateSubsetsWithWeightLimit(n, weights, C)
    % generateSubsetsWithWeightLimit
    %
    % Gera todos os subconjuntos de um conjunto de n elementos.
    % Os subconjuntos são filtrados com base na soma dos pesos.
    %
    % Argumentos:
    %   n: Número de elementos no conjunto.
    %   weights: Vetor de pesos (tamanho n).
    %   C: Valor máximo permitido para a soma dos pesos.
    %
    % Retorno:
    %   valid_subsets_matrix: Matriz binária (nxk) com os subconjuntos válidos.
    %   valid_sums_vector: Vetor-linha (1xk) com a soma dos pesos de cada subconjunto válido.

    % Validação de entrada: Garante que 'n' é um escalar e que os vetores 'weights'
    % e 'n' são compatíveis.
    if ~isscalar(n) || n < 0 || n ~= floor(n)
        error('O argumento "n" deve ser um inteiro não negativo.');
    end
    if length(weights) ~= n
        error('O tamanho do vetor de pesos deve ser igual a n.');
    end

    % 1. Gerar todos os 2^n subconjuntos como uma matriz binária.
    num_total_subsets = 2^n;
    all_subsets_matrix = logical(dec2bin(0:num_total_subsets-1) == '1');
    all_subsets_matrix = all_subsets_matrix';

    % 2. Calcule a soma dos pesos para cada subconjunto (coluna).
    % A multiplicação de matrizes 'weights' * 'all_subsets_matrix' calcula a soma
    % de cada coluna de forma vetorizada e eficiente.
    % O vetor 'weights' precisa ser um vetor-linha (1xn) para a multiplicação.
    total_weights_vector = weights(:)' * all_subsets_matrix;

    % 3. Filtre os subconjuntos com base na condição de peso.
    % 'find' retorna os índices das colunas que satisfazem a condição.
    valid_subset_indices = find(total_weights_vector <= C);

    % 4. Retorne as duas matrizes filtradas.
    % Matriz de subconjuntos válidos.
    valid_subsets_matrix = all_subsets_matrix(:, valid_subset_indices);

    % Vetor de somas válidas.
    valid_sums_vector = total_weights_vector(valid_subset_indices);
end
